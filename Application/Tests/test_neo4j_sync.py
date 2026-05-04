"""
Pytest suite for Neo4j sync logic.

Runs against the *local* Docker Neo4j container (expected at bolt://localhost:7687).
If local Neo4j is unavailable, tests are skipped.

To run:
    pytest Application/Tests/test_neo4j_sync.py -v
"""
import os
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch, call
from neo4j import GraphDatabase

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import sync module helpers
from Application.Scripts.sync_neo4j import (
    extract_topics,
    extract_relationships,
    merge_topics,
    merge_relationships,
    run_sync,
    _build_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _local_neo4j_available() -> bool:
    """Quick probe to see if local Neo4j Docker is up."""
    try:
        driver = GraphDatabase.driver(
            "bolt://localhost:7687", auth=("neo4j", "password")
        )
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception:
        return False


LOCAL_NEO4J_UP = _local_neo4j_available()


@pytest.fixture(scope="module")
def local_driver():
    """Yield a real driver to local Neo4j, skipping if down."""
    if not LOCAL_NEO4J_UP:
        pytest.skip("Local Neo4j Docker not available at bolt://localhost:7687")
    driver = GraphDatabase.driver(
        "bolt://localhost:7687", auth=("neo4j", "password")
    )
    yield driver
    driver.close()


@pytest.fixture(autouse=True)
def clean_local_db(local_driver):
    """Wipe Topic graph before each test to ensure isolation."""
    if LOCAL_NEO4J_UP:
        with local_driver.session(database="neo4j") as session:
            session.run("MATCH (t:Topic) DETACH DELETE t")
    yield


# ---------------------------------------------------------------------------
# Unit tests (mocked drivers)
# ---------------------------------------------------------------------------


def test_build_config_local():
    with patch.dict(
        os.environ,
        {"NEO4J_URI": "bolt://localhost:7687", "NEO4J_PASSWORD": "password"},
        clear=False,
    ):
        cfg = _build_config("local")
    assert cfg["uri"] == "bolt://localhost:7687"
    assert cfg["user"] == "neo4j"
    assert cfg["password"] == "password"


def test_build_config_cloud():
    with patch.dict(
        os.environ,
        {
            "NEO4J_URI": "mydb.databases.neo4j.io",
            "NEO4J_PASSWORD": "secret",
            "NEO4J_USERNAME": "neo4j",
        },
        clear=False,
    ):
        cfg = _build_config("cloud")
    assert cfg["uri"] == "neo4j+s://mydb.databases.neo4j.io:7687"
    assert cfg["password"] == "secret"


def test_build_config_missing_raises():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            _build_config("cloud")


def test_merge_topics_dry_run():
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

    topics = [{"name": "A"}, {"name": "B"}]
    count = merge_topics(mock_driver, "neo4j", topics, dry_run=True)
    assert count == 2
    mock_session.run.assert_not_called()


def test_merge_relationships_dry_run():
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

    pairs = [("A", "B"), ("B", "C")]
    count = merge_relationships(
        mock_driver, "neo4j", "PREREQUISITE", pairs, dry_run=True
    )
    assert count == 2
    mock_session.run.assert_not_called()


# ---------------------------------------------------------------------------
# Integration tests (real local Neo4j)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not LOCAL_NEO4J_UP, reason="Local Neo4j not available")
def test_extract_topics_empty(local_driver):
    topics = extract_topics(local_driver, "neo4j")
    assert topics == []


@pytest.mark.skipif(not LOCAL_NEO4J_UP, reason="Local Neo4j not available")
def test_extract_topics_and_relationships(local_driver):
    with local_driver.session(database="neo4j") as session:
        session.run(
            """
            CREATE (a:Topic {name: 'A', description: 'Desc A'})
            CREATE (b:Topic {name: 'B', description: 'Desc B'})
            CREATE (c:Topic {name: 'C'})
            CREATE (a)-[:PREREQUISITE]->(b)
            CREATE (b)-[:RELATED_TO]->(c)
            """
        )

    topics = extract_topics(local_driver, "neo4j")
    names = {t["name"] for t in topics}
    assert names == {"A", "B", "C"}

    prereqs = extract_relationships(local_driver, "neo4j", "PREREQUISITE")
    assert prereqs == [("A", "B")]

    related = extract_relationships(local_driver, "neo4j", "RELATED_TO")
    assert related == [("B", "C")]


@pytest.mark.skipif(not LOCAL_NEO4J_UP, reason="Local Neo4j not available")
def test_merge_topics_idempotent(local_driver):
    topics = [
        {"name": "T1", "description": "First"},
        {"name": "T2", "description": "Second"},
    ]
    merge_topics(local_driver, "neo4j", topics, dry_run=False)

    # Run again – should not create duplicates because of MERGE
    merge_topics(local_driver, "neo4j", topics, dry_run=False)

    with local_driver.session(database="neo4j") as session:
        count = session.run("MATCH (t:Topic) RETURN count(t) AS c").single()["c"]
    assert count == 2


@pytest.mark.skipif(not LOCAL_NEO4J_UP, reason="Local Neo4j not available")
def test_merge_relationships_idempotent(local_driver):
    # Seed nodes first
    with local_driver.session(database="neo4j") as session:
        session.run(
            "CREATE (:Topic {name: 'X'}), (:Topic {name: 'Y'})"
        )

    pairs = [("X", "Y")]
    merge_relationships(local_driver, "neo4j", "PREREQUISITE", pairs, dry_run=False)
    merge_relationships(local_driver, "neo4j", "PREREQUISITE", pairs, dry_run=False)

    with local_driver.session(database="neo4j") as session:
        count = session.run(
            "MATCH ()-[r:PREREQUISITE]->() RETURN count(r) AS c"
        ).single()["c"]
    assert count == 1


@pytest.mark.skipif(not LOCAL_NEO4J_UP, reason="Local Neo4j not available")
def test_run_sync_full_cycle(local_driver):
    """Treat one local DB as both source and target (self-sync sanity check)."""
    # Seed source data
    with local_driver.session(database="neo4j") as session:
        session.run(
            """
            CREATE (a:Topic {name: 'Math'})
            CREATE (b:Topic {name: 'Physics'})
            CREATE (a)-[:PREREQUISITE]->(b)
            """
        )

    cfg = {
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "password",
        "database": "neo4j",
    }

    stats = run_sync(cfg, cfg, dry_run=False)
    assert stats["topics"] == 2
    assert stats["prerequisites"] == 1
    assert stats["related_to"] == 0

    # Verify still exactly 2 topics / 1 prereq after sync
    with local_driver.session(database="neo4j") as session:
        t = session.run("MATCH (t:Topic) RETURN count(t) AS c").single()["c"]
        r = session.run(
            "MATCH ()-[r:PREREQUISITE]->() RETURN count(r) AS c"
        ).single()["c"]
    assert t == 2
    assert r == 1

