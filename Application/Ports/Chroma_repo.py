import os
import json
import logging
import threading
from typing import Any, Dict, List, Optional

try:
    import chromadb  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    chromadb = None

from langchain_huggingface import HuggingFaceEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ChromaRepo:
    """ChromaDB-backed vector store adapter.

    Implements the subset of the AstraRepo interface used by this project:
      - upsert_syllabus_chunks(texts, metadatas, topic_id=None)
      - similarity_search(query, k, filter=None, min_score=...)
      - vector_store property (raw Chroma collection)

    Similarity scoring:
      Chroma's returned `distance` is converted to a similarity-like score in [0, 1]
      using `score = 1 - distance`.
    """

    _instance: Optional["ChromaRepo"] = None
    _collection = None
    _lock = threading.Lock()

    collection_name: str

    def __new__(cls, collection_name: str = "syllabus_chunks"):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                # Important: assign before _init_vector_store()
                setattr(inst, "collection_name", collection_name)
                inst._init_vector_store()
                cls._instance = inst
            else:
                setattr(cls._instance, "collection_name", collection_name)
            return cls._instance

    def _init_vector_store(self):
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", str(os.getcwd()))
        chroma_path = os.path.join(persist_dir, "chroma_db")
        os.makedirs(chroma_path, exist_ok=True)

        if chromadb is None:
            raise ImportError("chromadb is not installed. Please install it using 'pip install chromadb'.")

        # New Chroma client API (avoids deprecated Settings)
        client = chromadb.PersistentClient(path=chroma_path)

        self._collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": os.getenv("CHROMA_SPACE", "cosine")},
        )

        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self._embedding = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        logger.info(
            f"✅ ChromaRepo initialized collection={self.collection_name} persist={chroma_path}"
        )

    def _make_ids(self, metadatas: List[Dict[str, Any]]) -> List[str]:
        topic_ids = [
            m.get("topic_id")
            or m.get("parent_topic_id")
            or m.get("course")
            or m.get("course_id")
            or ""
            for m in metadatas
        ]

        ids: List[str] = []
        for i, m in enumerate(metadatas):
            base = json.dumps(m, sort_keys=True, default=str)[:200]
            ids.append(f"{topic_ids[i]}:{hash(base)}:{i}")
        return ids

    def _apply_topic_id(
        self, metadatas: List[Dict[str, Any]], topic_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        if not topic_id:
            return metadatas
        out: List[Dict[str, Any]] = []
        for m in metadatas:
            mm = m.copy()
            mm["parent_topic_id"] = topic_id
            out.append(mm)
        return out

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def upsert_syllabus_chunks(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        topic_id: Optional[str] = None,
    ):
        if len(texts) < 5:
            logger.info(f"Skipping small upsert: {len(texts)} chunks")
            return
        if not self._collection:
            raise RuntimeError("ChromaRepo collection not initialized")
        if len(texts) != len(metadatas):
            raise ValueError("texts and metadatas must have same length")

        metadatas = self._apply_topic_id(metadatas, topic_id)
        ids = self._make_ids(metadatas)

        embeddings = self._embedding.embed_documents(texts)
        self._collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        logger.debug(
            f"Upserted {len(texts)} chunks to Chroma collection={self.collection_name}"
        )

    def _filter_to_chroma_where(
        self, filter: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not filter:
            return None
        # Accept already-formed where clauses
        if any(str(k).startswith("$") for k in filter.keys()):
            return filter
        # Simple equality mapping
        return {k: {"$eq": v} for k, v in filter.items()}

    def _distance_to_score(self, distance: float) -> float:
        # Convert cosine distance -> similarity-like score.
        score = 1.0 - float(distance)
        return max(0.0, min(1.0, score))

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def similarity_search(
        self,
        query: str,
        k: int = 8,
        filter: Optional[Dict[str, Any]] = None,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        if not self._collection:
            raise RuntimeError("ChromaRepo collection not initialized")

        q_emb = self._embedding.embed_query(query)
        where = self._filter_to_chroma_where(filter)

        res = self._collection.query(
            query_embeddings=[q_emb],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        documents = res.get("documents", [[]])[0]
        metadatas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0]

        out: List[Dict[str, Any]] = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            score = self._distance_to_score(dist)
            if score >= (min_score or 0):
                out.append({"document": doc, "metadata": meta or {}, "score": score})
        return out

    @property
    def vector_store(self):
        return self._collection
