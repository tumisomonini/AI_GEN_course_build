import os
from pathlib import Path
from typing import Generator, Optional
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


def sanitize_neo4j_uri(uri: str) -> str:
    '''Sanitize Neo4j URI - fix Aura to neo4j+s:// and ensure port.'''
    uri = uri.strip().rstrip('/')
    if '.databases.neo4j.io' in uri:
        if uri.startswith('bolt://'):
            uri = uri.replace('bolt://', 'neo4j+s://')
        elif '://' not in uri:
            uri = f'neo4j+s://{uri}'
        if ':7687' not in uri:
            uri = f'{uri}:7687'
    return uri

# Connection pools/singletons (thread-safe for FastAPI)
_postgres_repo = None
_astra_repo = None
_neo4j_repo = None
_astra_store = None

def init_neo4j_singleton():
    """Centralized Neo4j initialization: Local Docker first (fast/reliable), then cloud fallback."""
    global _neo4j_repo
    
    # Priority 1: Local Docker Neo4j (matches docker-compose: course_neo4j)
    local_uri = "bolt://localhost:7687"
    local_user = "neo4j"
    local_password = "password"  # From docker-compose NEO4J_AUTH
    local_database = "neo4j"
    
    import time
    def test_connection(uri, user, password, database=None, retries=5):
        for attempt in range(retries):
            try:
                repo = Neo4jRepoImpl(uri, user, password, database)
                with repo.driver.session(database=database) as session:
                    session.run("RETURN 1").single()
                return repo
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2)  # Wait for readiness
                    continue
                raise e
    
    # Try local first
    try:
        print("🔍 Testing local Neo4j (Docker)...")
        _neo4j_repo = test_connection(local_uri, local_user, local_password, local_database)
        print("✅ Local Neo4j connected")
        return _neo4j_repo
    except Exception as local_err:
        print(f"⚠️ Local Neo4j failed ({local_err}). Trying cloud Aura...")
    
    # Fallback: Cloud Aura
    raw_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    uri = sanitize_neo4j_uri(raw_uri)
    user = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD')
    database = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    try:
        _neo4j_repo = test_connection(uri, user, password, database)
        print("✅ Cloud Neo4j connected")
    except Exception as e:
        logging.warning(f"❌ All Neo4j connections failed: {e}")
        _neo4j_repo = None
    return _neo4j_repo

def get_postgres_repo() -> Generator[Optional[PostgresRepo], None, None]:
    """Dependency: PostgresRepo (auto-closes)."""
    global _postgres_repo
    try:
        if _postgres_repo is None:
            _postgres_repo = PostgresRepo()
    except Exception as e:
        logging.error(f"❌ Postgres initialization failed: {e}")
        _postgres_repo = None
        
    try:
        yield _postgres_repo
    finally:
        # No close on shared instance; handle in lifespan/shutdown
        pass

def get_astra_repo() -> Generator[Optional[AstraRepo], None, None]:
    """Dependency: AstraRepo."""
    global _astra_repo
    if _astra_repo is None:
        if os.getenv("ASTRA_DB_APPLICATION_TOKEN"):
            # Ensure HF_TOKEN is present for the embedding models used by Astra
            if not os.getenv("HF_TOKEN"):
                print("⚠️ Warning: HF_TOKEN not found in environment. Rate limits may apply. Set it in .env from https://huggingface.co/settings/tokens")
            _astra_repo = AstraRepo()
        else:
            print("⚠️ Astra DB token not configured")
            _astra_repo = None
    yield _astra_repo

def get_neo4j_repo() -> Generator[Optional[Neo4jRepoImpl], None, None]:
    """Dependency: Neo4jRepo (env-driven)."""
    global _neo4j_repo
    if _neo4j_repo is None:
        raw_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        uri = sanitize_neo4j_uri(raw_uri)

        user = os.getenv('NEO4J_USERNAME', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD')
        database = os.getenv('NEO4J_DATABASE', 'neo4j')
        try:
            _neo4j_repo = Neo4jRepoImpl(uri, user, password, database)
            # Perform a quick connectivity test
            with _neo4j_repo.driver.session(database=database) as session:
                session.run("RETURN 1").single()
            print(f"✅ Neo4j connection verified: {uri}")
        except Exception as e:
            print(f"⚠️ Neo4j connection failed at {uri}: {e}")
            # Step 7 Fallback: Attempt local Docker Neo4j if cloud connection fails
            if "localhost" not in uri:
                print("🔄 Attempting local fallback (bolt://localhost:7687)...")
                try:
                    _neo4j_repo = Neo4jRepoImpl("bolt://localhost:7687", "neo4j", "password")
                    with _neo4j_repo.driver.session() as session:
                        session.run("RETURN 1").single()
                    print("✅ Local Neo4j fallback successful")
                except Exception: pass
            if _neo4j_repo and not hasattr(_neo4j_repo, 'driver'):
                _neo4j_repo = None
                
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
