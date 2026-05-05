import os
import logging
import threading
from typing import List, Dict, Any, Optional
from langchain_astradb import AstraDBVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class AstraRepo:
    _instance: Optional['AstraRepo'] = None
    _vector_store: Optional[AstraDBVectorStore] = None
    _lock = threading.Lock()
    collection_name: str  # declared so Pylance resolves __new__ assignment

    def __new__(cls, collection_name: str = 'syllabus_chunks'):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.collection_name = collection_name
                try:
                    cls._instance._init_vector_store()
                except Exception:
                    # Reset singleton so the next attempt can retry cleanly
                    cls._instance = None
                    raise
            return cls._instance

    def _init_vector_store(self):
        token = os.getenv('ASTRA_DB_APPLICATION_TOKEN')
        db_id = os.getenv('ASTRA_DB_ID')
        api_endpoint = os.getenv('ASTRA_DB_ENDPOINT')

        if not token or not db_id:
            raise ValueError('Set ASTRA_DB_APPLICATION_TOKEN and ASTRA_DB_ID env vars')

        model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        embedding = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        if not api_endpoint:
            api_endpoint = f'https://{db_id}-us-east1.apps.astra.datastax.com'

        namespace = os.getenv('ASTRA_DB_NAMESPACE', 'default_keyspace')

        self._vector_store = AstraDBVectorStore(
            collection_name=self.collection_name,
            embedding=embedding,
            token=token,
            api_endpoint=api_endpoint,
            namespace=namespace
        )
        logger.debug(f"AstraRepo initialized: collection={self.collection_name}")

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def upsert_syllabus_chunks(self, texts: List[str], metadatas: List[Dict[str, Any]], topic_id: Optional[str] = None):
        """Enhanced upsert with hierarchical tagging."""
        if len(texts) < 5:
            logger.info(f"Skipping small upsert: {len(texts)} chunks")
            return
        if not self._vector_store:
            raise RuntimeError("AstraRepo vector store not initialized")
        enriched_metas = []
        for meta in metadatas:
            m = meta.copy()
            if topic_id:
                m['parent_topic_id'] = topic_id
            enriched_metas.append(m)

        batch_size = 50
        total_upserted = 0
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_metas = enriched_metas[i:i+batch_size]
            self._vector_store.add_texts(batch_texts, batch_metas)
            total_upserted += len(batch_texts)
        logger.debug(f"Upserted {total_upserted} chunks to AstraDB ({batch_size}-batches)")

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def similarity_search(self, query: str, k: int = 8, filter: Optional[Dict] = None, min_score: float = 0.5) -> List[Dict[str, Any]]:
        """Filtered similarity search to ensure quality grounding.
        Falls back to plain similarity_search if relevance-scored version unavailable.
        """
        if not self._vector_store:
            raise RuntimeError("AstraRepo vector store not initialized")

        try:
            results = self._vector_store.similarity_search_with_relevance_scores(query, k=k, filter=filter or None)
            filtered = [r for r in results if r[1] >= min_score]
            return [{'document': doc.page_content, 'metadata': doc.metadata, 'score': score} for doc, score in filtered]
        except (AttributeError, TypeError, NotImplementedError):
            logger.debug("similarity_search_with_relevance_scores unavailable, falling back to plain similarity_search")
            docs = self._vector_store.similarity_search(query, k=k, filter=filter or None)
            return [{'document': doc.page_content, 'metadata': doc.metadata, 'score': None} for doc in docs]

    @property
    def vector_store(self):
        return self._vector_store
