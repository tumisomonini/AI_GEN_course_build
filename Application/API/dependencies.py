import os
from pathlib import Path
from typing import Generator, Optional
from fastapi import Depends
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging
logger = logging.getLogger(__name__)
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

from neomodel import config as neomodel_config
load_dotenv(Path(__file__).resolve().parents[2] / '.env')



from Application.Ports.postgres_repo import PostgresRepo
from Application.Ports.neo4j_repo import Neo4jRepository as Neo4jRepoImpl
from Application.Ports.Astra_repo import AstraRepo
from Application.Ports.triple_db_manager import TripleDBManager


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
    """Centralized Neo4j initialization: prefer local Docker Neo4j first, then Aura cloud fallback."""

    global _neo4j_repo

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
    def test_connection(uri, user, password, database=None):
        if not password or not user:
            raise ValueError("Neo4j credentials missing")
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            # Verify routing + basic query
            conn = driver.verify_connectivity()
            print(f"✅ Neo4j connectivity: {conn}")
            with driver.session(database=database or 'neo4j') as session:
                session.run("RETURN 1", timeout=10.0).single()
            repo = Neo4jRepoImpl(uri, user, password, database)
            
            # Sync neomodel config and install constraints/labels
            neomodel_config.DATABASE_URL = f"bolt://{user}:{password}@{uri.split('://')[1]}"
            try:
                pass  # install_all_labels() removed in neomodel 6.x
            except Exception as e:
                print(f"⚠️ Neomodel label install warning (likely already exists): {e}")
            return repo
        finally:
            driver.close()

    # Local Docker first
    is_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER")
    local_uri = "bolt://neo4j:7687" if is_docker else "bolt://localhost:7687"
    local_user, local_pass, local_db = "neo4j", "password", "neo4j"
    print(f"🔍 Testing local Neo4j (Docker): {local_uri}")
    try:
        _neo4j_repo = test_connection(local_uri, local_user, local_pass, local_db)
        print("✅ Local Neo4j connected")
        return _neo4j_repo
    except Exception as local_err:
        print(f"⚠️ Local Neo4j failed: {local_err}. Falling back to Aura cloud...")

    # Cloud Aura fallback
    aura_uri = os.getenv('NEO4J_URI', '').strip()
    if '.neo4j.io' in aura_uri:
        aura_user = os.getenv('NEO4J_USERNAME', 'neo4j')
        aura_pass = os.getenv('NEO4J_PASSWORD')
        aura_db = os.getenv('NEO4J_DATABASE', 'neo4j')
        sanitized_uri = sanitize_neo4j_uri(aura_uri)
        print(f"🔍 Testing Aura cloud Neo4j: {sanitized_uri}")
        try:
            _neo4j_repo = test_connection(sanitized_uri, aura_user, aura_pass, aura_db)
            print("✅ Aura Neo4j connected & set as default")
            return _neo4j_repo
        except Exception as cloud_err:
            print(f"❌ Aura failed ({cloud_err}).")

    print("❌ Neo4j connection failed: neither local Docker nor Aura reachable")
    _neo4j_repo = None
    return None
    # If successful, _neo4j_repo would have been set and returned earlier.

def init_postgres_singleton() -> Optional[PostgresRepo]:
    """Centralized Postgres initialization with schema enforcement."""
    global _postgres_repo
    if _postgres_repo is not None:
        return _postgres_repo

    def _init():
        repo = PostgresRepo()
        try:
            repo.init_schema()
        except Exception as schema_e:
            err_str = str(schema_e).lower()
            if 'duplicate' in err_str or 'already exists' in err_str:
                print(f"⚠️ Schema init: tables already exist ({schema_e})")
            else:
                raise
        return repo

    try:
        _postgres_repo = _init()
        print("✅ Postgres repository and schema ready")
    except Exception as e:
        logging.error(f"❌ Postgres initialization failed: {e}")
        _postgres_repo = None
    return _postgres_repo

def get_postgres_repo() -> Generator[Optional[PostgresRepo], None, None]:
    """Dependency: PostgresRepo singleton."""
    repo = init_postgres_singleton()
    yield repo



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
    """Centralized AstraDB initialization with retry. MANDATORY."""
    global _astra_repo
    if _astra_repo is not None:
        return _astra_repo

    # Fail-fast if credentials are missing — Astra is now mandatory
    if not os.getenv('ASTRA_DB_APPLICATION_TOKEN') or not os.getenv('ASTRA_DB_ID'):
        raise ValueError("❌ AstraDB is MANDATORY: Set ASTRA_DB_APPLICATION_TOKEN and ASTRA_DB_ID env vars")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def test_astra():
        repo = AstraRepo()
        # Light check: init success, no upsert/search
        assert repo.vector_store is not None
        return repo

    try:
        print("🔍 Initializing AstraDB (mandatory)...")
        _astra_repo = test_astra()
        print("✅ AstraDB connected")
    except Exception as e:
        raise ValueError(f"❌ AstraDB initialization failed (mandatory): {e}")
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
    """Get vector store for RAG.

    Preference order:
      1) AstraDB (if configured)
      2) ChromaDB local embedded fallback
    """
    try:
        repo = init_astra_singleton()
        if repo:
            return repo.vector_store
    except Exception as e:
        logger.warning(f"Astra init failed, falling back to local vector store: {e}")

    print("⚠️ Vector store: using local ChromaDB fallback")
    try:
        from Application.Infrastructure.vectorDb.Chroma_vector_store import get_chroma_vector_store
        local_store = get_chroma_vector_store()
        if local_store:
            return local_store
    except Exception as e:
        logger.warning(f"Chroma fallback failed: {e}")

    return None





def get_triple_db_manager():
    try:
        return TripleDBManager()
    except ValueError as e:
        print(f"❌ TripleDBManager failed: {e}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def check_all_dbs():
    """
    Comprehensive health check for all databases with retries.
    Critical: Postgres + Neo4j must succeed.
    Optional: Astra (warns if missing).
    """
    global _postgres_repo, _neo4j_repo, _astra_repo
    results = {}

    # Postgres
    try:
        if _postgres_repo is None:
            raise ValueError("Postgres not initialized")
        _postgres_repo.search_courses('')  # lightweight ORM connectivity check
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

    # Astra (MANDATORY — raise if unavailable)
    try:
        if _astra_repo is None:
            init_astra_singleton()
        if _astra_repo and _astra_repo.vector_store is not None:
            results['astra'] = 'healthy'
            print("✅ AstraDB health OK")
        else:
            raise ValueError("AstraDB vector store not initialized")
    except Exception as e:
        results['astra'] = f'error: {str(e)}'
        raise Exception(f"Critical: AstraDB unhealthy (mandatory) - {e}")

    print(f"🌐 DBs checked: {results}")
    return results
