import os
from pathlib import Path
from typing import Generator, Optional
from fastapi import Depends
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv(Path(__file__).resolve().parents[2] / '.env')



from Application.Ports.postgres_repo import PostgresRepo
from Application.Ports.neo4j_repo import Neo4jRepository as Neo4jRepoImpl
from Application.Ports.Astra_repo import AstraRepo


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
_neo4j_repo = None
_astra_repo = None

def init_neo4j_singleton():
    """Centralized Neo4j initialization: Local Docker first (fast/reliable), then cloud fallback."""
    global _neo4j_repo
    
    # Detect if we are running inside Docker to use the correct service hostname
    is_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "true"
    # Inside Docker, the service is 'neo4j'. Outside, it is 'localhost'.
    local_uri = "bolt://neo4j:7687" if is_docker else "bolt://localhost:7687"
    local_user = "neo4j"
    local_password = "password"  # From docker-compose NEO4J_AUTH
    local_database = "neo4j"
    
    import time
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def test_connection(uri, user, password, database=None):
        if not password:
            raise ValueError("Credentials missing for Neo4j")
        repo = Neo4jRepoImpl(uri, user, password, database)
        with repo.driver.session(database=database) as session:
            session.run("RETURN 1", timeout=5.0).single()
        return repo

    # Try local first
    try:
        print("🔍 Testing local Neo4j (Docker)...")
        _neo4j_repo = test_connection(local_uri, local_user, local_password, local_database)
        print("✅ Local Neo4j connected")
        return _neo4j_repo
    except Exception as local_err:
        raise RuntimeError(f"Local Neo4j failed: {local_err}. Ensure Docker Neo4j running (cd Application/Docker && docker-compose up -d neo4j). Cloud fallback disabled.") from local_err

    return _neo4j_repo

def get_postgres_repo() -> Generator[Optional[PostgresRepo], None, None]:
    """Dependency: PostgresRepo (auto-closes)."""
    global _postgres_repo
    # Lazy initialization with retry logic if the previous attempt failed
    if _postgres_repo is None:
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
        def _init_postgres():
            repo = PostgresRepo()
            repo.init_schema()  # Ensure schema ready
            return repo
        
        try:
            _postgres_repo = _init_postgres()
            print("✅ Postgres repository initialized successfully")
        except Exception as e:
            logging.error(f"❌ Postgres initialization failed: {e}")
            _postgres_repo = None
        
    try:
        yield _postgres_repo
    finally:
        # No close on shared instance; handle in lifespan/shutdown
        pass



def get_neo4j_repo() -> Generator[Optional[Neo4jRepoImpl], None, None]:
    """Dependency: Neo4jRepo (env-driven)."""
    global _neo4j_repo
    if _neo4j_repo is None:
        init_neo4j_singleton()
    try:
        yield _neo4j_repo
    finally:
        pass  # Close in lifespan

def init_astra_singleton():
    """Centralized AstraDB initialization with retry."""
    global _astra_repo
    if _astra_repo is not None:
        return _astra_repo

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=30))
    def test_astra():
        repo = AstraRepo()
        # Light check: init success, no upsert/search
        assert repo.vector_store is not None
        return repo

    try:
        print("🔍 Initializing AstraDB...")
        _astra_repo = test_astra()
        print("✅ AstraDB connected")
    except Exception as e:
        print(f"⚠️ AstraDB failed: {e}. Vector RAG disabled.")
        _astra_repo = None
    return _astra_repo

def get_astra_repo() -> Generator[Optional[AstraRepo], None, None]:
    """Dependency: AstraRepo singleton."""
    global _astra_repo
    if _astra_repo is None:
        init_astra_singleton()
    try:
        yield _astra_repo
    finally:
        pass

def get_vector_store():
    """Get vector store for RAG (Astra first, warn if down)."""
    repo = init_astra_singleton()
    if repo:
        return repo.vector_store
    print("⚠️ Astra unavailable, RAG disabled")
    return None





@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def check_all_dbs():
    """
    Comprehensive health check for all databases with retries.
    Critical: Postgres + Neo4j must succeed.
    Optional: Astra (warns if missing).
    """
    global _postgres_repo, _neo4j_repo
    results = {}

    # Postgres
    try:
        if _postgres_repo is None:
            raise ValueError("Postgres not initialized")
        with _postgres_repo.get_cursor() as cur:
            cur.execute("SELECT 1")
        results['postgres'] = 'healthy'
        print("✅ Postgres health OK")
    except Exception as e:
        results['postgres'] = f'error: {str(e)}'
        raise Exception(f"Critical: Postgres unhealthy - {e}")

    # Neo4j
    try:
        if _neo4j_repo is None:
            raise ValueError("Neo4j not initialized")
        database = os.getenv('NEO4J_DATABASE', 'neo4j')
        with _neo4j_repo.driver.session(database=database) as session:
            session.run("RETURN 1").single()
        results['neo4j'] = 'healthy'
        print("✅ Neo4j health OK")
    except Exception as e:
        results['neo4j'] = f'error: {str(e)}'
        raise Exception(f"Critical: Neo4j unhealthy - {e}")

    print(f"🌐 DBs checked: {results}")
    return results
