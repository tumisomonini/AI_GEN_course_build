import pytest
import os
from Application.API.dependencies import check_all_dbs, _postgres_repo, _neo4j_repo

@pytest.fixture(scope='session')
def db_setup():
    \"\"\"Skip if no DBs configured for CI.\"\"\"
    if not os.getenv('POSTGRES_HOST') and not os.getenv('NEO4J_URI'):
        pytest.skip('DB env not set - skipping live tests')

def test_check_all_dbs_healthy():
    \"\"\"Test comprehensive DB health check passes.\"\"\"
    try:
        results = check_all_dbs()
        # Critical must be healthy
        assert results['postgres'] == 'healthy'
        assert results['neo4j'] == 'healthy'
        print(f'✅ DB health: {results}')
    except Exception as e:
        pytest.fail(f'DB health check failed: {e}')

def test_postgres_singleton():
    \"\"\"Verify PostgresRepo singleton inits.\"\"\"
    from Application.Ports.postgres_repo import PostgresRepo
    repo = PostgresRepo()
    assert repo is not None
    assert hasattr(repo, 'repo')

def test_neo4j_singleton():
    \"\"\"Verify Neo4jRepo singleton.\"\"\"
    global _neo4j_repo
    assert _neo4j_repo is not None
    assert hasattr(_neo4j_repo, 'driver')
