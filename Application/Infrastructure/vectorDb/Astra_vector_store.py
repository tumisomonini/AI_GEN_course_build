from typing import List, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv
import cassio
from sentence_transformers import SentenceTransformer

load_dotenv(Path(__file__).resolve().parents[3] / '.env')

_embedding_model = None

def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

class AstraVectorStore:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        token = os.getenv("ASTRA_TOKEN") or os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        db_id = os.getenv("ASTRA_DB_ID")
        if not token or not db_id:
            print("⚠️ AstraDB: Missing ASTRA_DB_APPLICATION_TOKEN or ASTRA_DB_ID")
            self.collection = None
            return
        try:
            cassio.init(
                token=token,
                database_id=db_id,
            )
            from cassio.vector import VectorTable
            self.collection = VectorTable(collection_name, vector_dimension=384)
            print(f"✅ AstraDB '{collection_name}' initialized")
        except Exception as e:
            print(f"❌ AstraDB init failed: {e}")
            self.collection = None

    @property
    def embedding_model(self) -> SentenceTransformer:
        return _get_embedding_model()

    def upsert_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        if self.collection is None:
            print("⚠️ AstraDB: Vector store not available, skipping upsert")
            return
        if metadatas is None:
            metadatas = [{} for _ in texts]
        embeddings = self.embedding_model.encode(texts).tolist()
        for i, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
            self.collection.put(
                document=text,
                embedding_vector=embedding,
                document_id=str(i),
                metadata=metadata,
            )

    def query(self, query_text: str, k: int = 5, filter: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if self.collection is None:
            print("⚠️ AstraDB: Vector store not available, returning empty results")
            return []
        query_embedding = self.embedding_model.encode([query_text])[0].tolist()
        # Cassio VectorTable supports metadata filtering via the 'metadata' kwarg
        return self.collection.search(
            embedding_vector=query_embedding, 
            top_k=k,
            metadata=filter
        )
