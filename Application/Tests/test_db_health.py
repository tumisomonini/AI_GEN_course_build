import pytest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from Application.API.dependencies import check_all_dbs, _postgres_repo, _neo4j_repo, init_neo4j_singleton, init_postgres_singleton

@pytest.fixture(scope='session')
def db_setup():
    """Skip if no DBs configured for CI."""
    if not os.getenv('POSTGRES_HOST') and not os.getenv('NEO4J_URI'):
        pytest.skip('DB env not set - skipping live tests')

def test_triple_db_manager():
    """Test TripleDBManager integration."""
    from Application.API.dependencies import get_triple_db_manager
    manager = get_triple_db_manager()
    health = manager.get_health()
    # Astra is optional, Postgres and Neo4j must be healthy
    assert health['postgres'] == 'healthy'
    assert health['neo4j'] == 'healthy'
    print(f'✅ TripleDB health: {health}')

def test_check_all_dbs_healthy():
    """Legacy test."""
    global _postgres_repo, _neo4j_repo
    # Ensure singletons are initialized before checking
    if _postgres_repo is None:
        init_postgres_singleton()
    if _neo4j_repo is None:
        init_neo4j_singleton()
    # Skip if either DB is not available
    if _postgres_repo is None:
        pytest.skip('Postgres not available')
    if _neo4j_repo is None:
        pytest.skip('Neo4j not available')
    try:
        results = check_all_dbs()
        assert results['postgres'] == 'healthy'
        assert results['neo4j'] == 'healthy'
    except Exception as e:
        pytest.fail(f'Legacy DB health check failed: {e}')

def test_postgres_singleton():
    """Verify PostgresRepo singleton inits with schema."""
    from Application.Ports.postgres_repo import PostgresRepo
    repo = PostgresRepo()
    assert repo is not None
    repo.init_schema()  # Ensure schema sync
    assert hasattr(repo.repo, 'engine')  # Verify engine exists
    repo.close()

def test_neo4j_singleton():
    """Verify Neo4jRepo singleton."""
    global _neo4j_repo
    if _neo4j_repo is None:
        init_neo4j_singleton()
    if _neo4j_repo is None: # If init_neo4j_singleton failed, skip the test
        pytest.skip('Neo4j not available - local Docker may not be running')
    assert _neo4j_repo is not None
    assert hasattr(_neo4j_repo, 'driver')
