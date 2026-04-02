from typing import List, Dict, Any
import os
from dotenv import load_dotenv
import cassio
from sentence_transformers import SentenceTransformer

load_dotenv()

_embedding_model = None

def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

class AstraVectorStore:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        cassio.init(
            token=os.getenv("ASTRA_TOKEN") or os.getenv("ASTRA_DB_APPLICATION_TOKEN"),
            database_id=os.getenv("ASTRA_DB_ID"),
        )
        from cassio.vector import VectorTable
        self.collection = VectorTable(collection_name, dimension=384)

    @property
    def embedding_model(self) -> SentenceTransformer:
        return _get_embedding_model()

    def upsert_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        if metadatas is None:
            metadatas = [{} for _ in texts]
        embeddings = self.embedding_model.encode(texts).tolist()
        self.collection.put(
            objects=[
                {
                    "id": i,
                    "text": text,
                    "metadata": metadata,
                    "embedding": embedding,
                }
                for i, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas))
            ]
        )

    def query(self, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_model.encode([query_text])[0].tolist()
        results = self.collection.similarity_search(
            query_embedding, k=k
        )
        return results
