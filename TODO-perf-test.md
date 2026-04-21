# Performance Optimization Test Plan & Progress

## Status: In Progress [Step 1/9]

**Goal**: Verify syllabus generation perf (2-5min total, asyncio concurrency, no 500s/timeouts).

### Steps:
- [x] 1. Install deps & populate DBs (Docker up, local venv torch issue skipped)
- [x] 2. Start Docker DBs/server (DBs up, api building, health degraded)
- [ ] 3. Test /health
- [ ] 4. Time /syllabus/generate API (curl)
- [ ] 5. pytest workflow
- [ ] 6. UI end-to-end test
- [ ] 7. Measure generation_time from logs
- [ ] 8. Profile bottlenecks if slow
- [ ] 9. Document results & attempt_completion

**Baseline target**: 6 chapters, ~120s total, validated=True.

**Notes**: Needs API key? Docker? Logs captured.

