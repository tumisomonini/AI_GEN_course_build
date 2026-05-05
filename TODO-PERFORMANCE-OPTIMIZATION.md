# Performance Optimization TODO (from Table: ~95% Latency Reduction)
Current: [ ] Baseline perf_test.py results saved

## 1. Parallelize Author Agent (50% impact - LangGraph) ✅
- [x] Edit syllabus_workflow.py: Conditional parallel author→reviewer (skip if validated)
- [x] Edit Author_agent.py: max_concurrent=5, retrieval to_thread()
**Test**: pytest test_author_agent.py + perf_test [ ]

## 2. Async I/O External Calls (30% impact) ✅ Partial
- [x] triple_db_manager.hybrid_search → async wrapper w/ executor
- [ ] Postgres/Neo4j repos → async methods (Step 3 DB)
**Test**: Full workflow run [ ]

## 3. DB Indexes (10% impact) ✅
- [x] migrations/0002_add_perf_indexes.py created (logs.run_id, courses.title/status, etc.)
- [ ] Run: cd Application && alembic upgrade head
**Test**: [ ] EXPLAIN ANALYZE SELECT * FROM logs WHERE run_id=1;

## 4. GZip Compression (5% impact)
- [ ] Main.py: Add GZipMiddleware
**Test**: curl response sizes

## Validation
- [ ] Run perf_test.py → compare before/after
- [ ] pytest full suite
- [ ] Production deploy (docker-compose up)

Progress tracked here. Next: Step 1 complete → mark & Step 2.
