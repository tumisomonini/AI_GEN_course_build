# Neo4j initialization (local)

## Goal

Bring up the local Neo4j service and verify connectivity from the app.

## Steps

1. Start Neo4j via Docker Compose.
2. Wait for `course_neo4j` healthcheck to pass.
3. Verify connectivity using `test_local_neo4j.py` (bolt://localhost:7687, neo4j/password).
4. If needed, run `python Application/Scripts/init_neo4j.py` to also populate sample Topic nodes/relationships.
5. Re-run `pytest -k neo4j` to confirm Neo4j integration tests pass.
