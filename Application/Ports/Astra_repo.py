import os
import json
import logging
import threading
from typing import List, Dict, Any, Optional
from langchain_astradb import AstraDBVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
import asyncio
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class AstraRepo:
    _instance = None
    _vector_store = None
    _lock = threading.Lock()

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
        # Use CPU to avoid GPU/MPS issues; cache model locally
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
    async def aupsert_syllabus_chunks(self, texts: List[str], metadatas: List[Dict[str, Any]], topic_id: Optional[str] = None):
        """Async upsert with hierarchical tagging."""
        if len(texts) < 5:
            logger.info(f"Skipping small upsert: {len(texts)} chunks")
            return
        if not self._vector_store:
            raise RuntimeError("AstraRepo vector store not initialized")
        await asyncio.to_thread(self._sync_upsert_syllabus_chunks, texts, metadatas, topic_id)

    def _sync_upsert_syllabus_chunks(self, texts: List[str], metadatas: List[Dict[str, Any]], topic_id: Optional[str] = None):
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
    async def asimilarity_search(self, query: str, k: int = 8, filter: Optional[Dict] = None, min_score: float = 0.7) -> List[Dict[str, Any]]:
        """Async filtered similarity search with Redis caching and score filtering."""
        import hashlib
        import redis
        from dotenv import load_dotenv
        load_dotenv()
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        try:
            r = redis.from_url(redis_url, decode_responses=True)
            r.ping()
        except Exception:
            logger.warning('Redis unavailable, skipping cache')
            r = None
        
        cache_key = f'rag:{hashlib.sha256(query.encode()).hexdigest()}:{k}'
        
        if r:
            cached = r.get(cache_key)
            if cached and isinstance(cached, str):
                logger.debug(f'Cache HIT for RAG query: {query[:50]}')
                return json.loads(cached)
        
        if not self._vector_store:
            raise RuntimeError('AstraRepo vector store not initialized')
        
        results = await asyncio.to_thread(self._sync_similarity_search, query, k, filter, min_score)
        
        # Filter high-quality only
        high_quality = [res for res in results if res.get('score', 0) and res['score'] > min_score]
        
        if r and high_quality:
            r.setex(cache_key, 3600, json.dumps(high_quality))  # 1h TTL
        
        return high_quality

    def _sync_similarity_search(self, query: str, k: int = 8, filter: Optional[Dict] = None, min_score: float = 0.7) -> List[Dict[str, Any]]:
        try:
            results = self._vector_store.similarity_search_with_relevance_scores(query, k=k, filter=filter or None)
            filtered = [r for r in results if r[1] >= min_score]
            return [{'document': doc.page_content, 'metadata': doc.metadata, 'score': score} for doc, score in filtered]
        except (AttributeError, TypeError, NotImplementedError):
            logger.debug('similarity_search_with_relevance_scores unavailable, falling back')
            docs = self._vector_store.similarity_search(query, k=k, filter=filter or None)
            return [{'document': doc.page_content, 'metadata': doc.metadata, 'score': None} for doc in docs]

    # Legacy sync aliases
    def upsert_syllabus_chunks(self, texts: List[str], metadatas: List[Dict[str, Any]], topic_id: Optional[str] = None):
        asyncio.run(self.aupsert_syllabus_chunks(texts, metadatas, topic_id))

    def similarity_search(self, query: str, k: int = 8, filter: Optional[Dict] = None, min_score: float = 0.7) -> List[Dict[str, Any]]:
        return asyncio.run(self.asimilarity_search(query, k, filter, min_score))





    @property
    def vector_store(self):
        return self._vector_store

