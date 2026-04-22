import os
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import astradb
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

class AstraRepo:
    _instance = None
    _vector_store = None

    def __new__(cls, collection_name: str = 'syllabus_chunks'):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.collection_name = collection_name
            cls._instance._init_vector_store()
        return cls._instance

    def _init_vector_store(self):
        token = os.getenv('ASTRA_DB_APPLICATION_TOKEN')
        db_id = os.getenv('ASTRA_DB_ID')
        if not token or not db_id:
            raise ValueError('Set ASTRA_DB_APPLICATION_TOKEN and ASTRA_DB_ID env vars')

        embedding = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2', timeout=30.0)

        api_endpoint = f'https://{db_id}-us-east1.apps.astra.datastax.com'

        self._vector_store = astradb.AstraDB(
            collection_name=self.collection_name,
            embedding=embedding,
            token=token,
            api_endpoint=api_endpoint,
            collection_setup_mode=astradb.SetupMode.SYNC,
        )
        print(f'✅ AstraRepo initialized: collection={self.collection_name}')

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=1, max=10))
    def upsert_syllabus_chunks(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        docs = [Document(page_content=text, metadata=meta) for text, meta in zip(texts, metadatas)]
        self._vector_store.add_documents(docs)
        print(f'✅ Upserted {len(texts)} chunks to AstraDB')

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=1, max=10))
    def similarity_search(self, query: str, k: int = 8, filter: Optional[Dict] = None) -> List[Dict[str, Any]]:
        results = self._vector_store.similarity_search(query, k=k, filter=filter or None)
        return [{'document': doc.page_content, 'metadata': doc.metadata, 'score': 0.9} for doc in results]  # Mock score

    @property
    def vector_store(self):
        return self._vector_store
