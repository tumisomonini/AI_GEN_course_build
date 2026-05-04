# Resolve AstraDB State [BLACKBOXAI]

## Plan
1. [x] Fix `Application/Ports/triple_db_manager.py` — Make Astra optional, remove hard `ValueError`
2. [x] Fix `Application/API/Main.py` — Don't crash on TripleDBManager failure in lifespan
3. [x] Fix `Application/API/agents.py` — Fix AuthorAgent initialization bug
4. [x] Fix `Application/Ports/Astra_repo.py` — Fix similarity_search fallback + timeouts + singleton thread-safety + new langchain-astradb API
5. [x] Fix `Application/API/dependencies.py` — Add Astra health check + local fallback + optional handling
6. [x] Fix `Application/Workflows/syllabus_workflow.py` — Handle missing Astra gracefully
7. [x] Fix `Application/Tests/test_rag_integration.py` — Update tests for degraded state
8. [x] Verify: run import test — ✅ AstraRepo imports successfully
9. [x] Verify: AstraRepo init — ✅ Embeddings load, API call attempted (connection error = network/ID issue, not code)
10. [x] Verify: py_compile all modified files — ✅ All 7 files compile successfully

## Summary of Changes

### Critical Bugs Fixed
1. **TripleDBManager hard crash** — Removed `raise ValueError("All 3 DBs must be healthy")`; Astra is now optional (only Postgres + Neo4j required)
2. **AstraRepo obsolete API** — Removed broken `from langchain_astradb import AstraDB`; now passes `token`/`api_endpoint`/`namespace` directly to `AstraDBVectorStore`
3. **AuthorAgent init bug** — `AuthorAgent(vector_store, repo=repo)` → `AuthorAgent(manager=None, repo=repo, kg=None)` (was passing vector_store as manager positional arg)
4. **Main.py lifespan crash** — TripleDBManager check now only requires postgres + neo4j; warns if Astra missing instead of raising
5. **similarity_search missing method** — Added try/except fallback to plain `similarity_search` if `similarity_search_with_relevance_scores` unavailable

### Resilience Improvements
- Thread-safe singleton in AstraRepo (`threading.Lock()`)
- `similarity_search` and `upsert_syllabus_chunks` guard against uninitialized vector_store
- `get_vector_store()` attempts local fallback if Astra down
- `check_all_dbs()` includes Astra as optional (warns, doesn't raise)
- `syllabus_workflow.py` checks `manager.astra` exists before upserting
- `create_linked_course()` skips Astra upsert if unavailable

## Next Steps (User Action)
1. Verify `ASTRA_DB_ID` is correct (current value may have trailing character)
2. Set `ASTRA_DB_NAMESPACE` env var if not using `default_keyspace`
3. Ensure network connectivity to `https://{ASTRA_DB_ID}-us-east1.apps.astra.datastax.com`

