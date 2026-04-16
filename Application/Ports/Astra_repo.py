from typing import List, Dict, Any
from Application.Infrastructure.vectorDb.Astra_vector_store import AstraVectorStore


class AstraRepo:
    def __init__(self, collection_name: str = "syllabus_chunks"):
        self.vector_store = AstraVectorStore(collection_name)

    def upsert_syllabus_chunks(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        """Upsert scraped syllabus text chunks to AstraDB"""
        self.vector_store.upsert_texts(texts, metadatas)

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Vector similarity search"""
        return self.vector_store.query(query, k=k)
