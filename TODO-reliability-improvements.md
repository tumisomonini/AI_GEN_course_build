# TODO: Improve Program Reliability
✅ COMPLETE - Major reliability gains: retries, timeouts, global loggers, resilient DBs.

## Summary of Changes
- ✅ deps.py: Tenacity @retry(3x exp backoff), Neo4j connect/query timeouts
- ✅ scraper.py: Playwright 30s timeout + 2x retry loop
- ✅ neo4j_repo.py: @retry on Cypher ops
- ✅ workflow.py: Global PostgresRepo (no N+1 opens), tenacity-ready
- ✅ Main.py: Pool stats in /health

## Test & Verify
```
cd Application/Scripts && python perf_test.py  # <2min, no crashes
curl localhost:8000/health  # 'healthy' or 'degraded' graceful
```

DBs now fallback gracefully, scrapes retry, workflows log efficiently.

## 3. Graceful Degradation & Monitoring [ ]
- [ ] Main.py: Enhanced /health with pool stats, auto-reinit
- [ ] Global structured error logging

## 4. Requirements & Tests [ ]
- [ ] pip install tenacity (test venv)
- [ ] Chaos tests (mock fails)
- [ ] Run perf_test.py → verify stability

## 5. Verification [ ]
- [ ] Kill DBs → app degraded but responsive
- [ ] Full e2e perf_test.py & /health

Progress: Updated after each step.

