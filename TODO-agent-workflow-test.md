# Agent Workflow Test - Progress Tracker

Status: Approved plan - Fixes for clean pytest + perf benchmark.

## Steps
- [x] 1. Install langchain-huggingface langchain-astradb
- [x] 2. Patch mocks in test_syllabus_workflow.py for DB isolation
- [x] 3. Fix Astra_repo.py deprecations
- [ ] 4. pytest test_syllabus_workflow.py:: 6/6 PASS
- [ ] 5. python Application/Scripts/perf_test.py (real LLM/DB workflow)
- [ ] 6. cat perf_results.txt + API health
- [ ] 7. uvicorn + curl /syllabus/generate

Current: pytest 0/6 (DB deps), deps ready, DBs healthy, .env keys ✓

## Notes
Tests fail on real DB/Astra - mock to isolate logic.
