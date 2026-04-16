import os
from pathlib import Path
from typing import Generator
from fastapi import Depends
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

# Normalize HF_TOKEN from environment variations (e.g., HF_Token, hf_token)
hf_val = os.getenv("HF_TOKEN") or os.getenv("HF_Token") or os.getenv("hf_token")
if hf_val:
    os.environ["HF_TOKEN"] = hf_val

# Suppress noisy model load reports and unexpected key warnings from transformers
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

from Application.Ports.postgres_repo import PostgresRepo
from Application.Ports.Astra_repo import AstraRepo
from Application.Ports.neo4j_repo import Neo4jRepository as Neo4jRepoImpl
from Application.Infrastructure.vectorDb.Astra_vector_store import AstraVectorStore

# Connection pools/singletons (thread-safe for FastAPI)
_postgres_repo = None
_astra_repo = None
_neo4j_repo = None
_astra_store = None

def get_postgres_repo() -> Generator[PostgresRepo, None, None]:
    """Dependency: PostgresRepo (auto-closes)."""
    global _postgres_repo
    if _postgres_repo is None:
        _postgres_repo = PostgresRepo()
    try:
        yield _postgres_repo
    finally:
        # No close on shared instance; handle in lifespan/shutdown
        pass

def get_astra_repo() -> Generator[AstraRepo, None, None]:
    """Dependency: AstraRepo."""
    global _astra_repo
    if _astra_repo is None:
        if os.getenv("ASTRA_DB_APPLICATION_TOKEN"):
            # Ensure HF_TOKEN is present for the embedding models used by Astra
            if not os.getenv("HF_TOKEN"):
                print("⚠️ Warning: HF_TOKEN not found in environment. Rate limits may apply. Set it in .env from https://huggingface.co/settings/tokens")
            _astra_repo = AstraRepo()
        else:
            raise ValueError("Astra DB token not configured")
    yield _astra_repo

def get_neo4j_repo() -> Generator[Neo4jRepoImpl, None, None]:
    """Dependency: Neo4jRepo (env-driven)."""
    global _neo4j_repo
    if _neo4j_repo is None:
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USERNAME', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD')
        database = os.getenv('NEO4J_DATABASE')
        try:
            _neo4j_repo = Neo4jRepoImpl(uri, user, password, database)
            # Perform a quick connectivity test
            with _neo4j_repo.driver.session() as session:
                session.run("RETURN 1").single()
            print(f"✅ Neo4j connection verified: {uri}")
        except Exception as e:
            print(f"❌ Neo4j connection failed at {uri}: {e}")
            _neo4j_repo = None # Reset to allow retry on next request
    try:
        yield _neo4j_repo
    finally:
        pass  # Close in lifespan

def get_astra_vector_store(collection_name: str = 'course_chunks') -> AstraVectorStore:
    """For agents (non-generator)."""
    global _astra_store
    if _astra_store is None or _astra_store.collection_name != collection_name:
        token = os.getenv('ASTRA_DB_APPLICATION_TOKEN')
        endpoint = os.getenv('ASTRA_DB_API_ENDPOINT')
        _astra_store = AstraVectorStore(collection_name, token, endpoint)
    return _astra_store
