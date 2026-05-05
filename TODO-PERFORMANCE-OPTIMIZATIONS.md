# AI_GEN_course_build Performance Optimizations TODO

## Phase 1: Quick Wins (Target: 40% latency reduction)
- [x] 1. DB Indexes: Verified `migrations/versions/0002_add_perf_indexes.py` already optimal (CONCURRENTLY idx_chapters_course_status, idx_runs_status etc.)
- [x] 2. Workflow Async: Updated `Application/Workflows/syllabus_workflow.py` (async planner/assemble nodes w/ run_in_executor)
- [x] 3. TripleDB Async: Updated `Application/Ports/triple_db_manager.py` (parallel KG calls, async vector prefer)
- [ ] 4. Dependencies: Update `Application/requirements.txt`
- [ ] 5. Test: `Application/Scripts/perf_test.py` → new baseline (target mean <25s, std<2s)
- [ ] 6. Deploy: `uvicorn Application.API.Main_fixed:app --reload`

**Progress: 3/6 Phase 1**  
**Next: Dependencies**
- [ ] 4. Dependencies: Update `Application/requirements.txt`
- [ ] 5. Test: `Application/Scripts/perf_test.py` → new baseline (target mean <25s, std<2s)
- [ ] 6. Deploy: `uvicorn Application.API.Main_fixed:app --reload`

**Progress: 2/6 Phase 1**  
**Next: TripleDB async**
- [ ] 3. TripleDB Async: Edit `Application/Ports/triple_db_manager.py` (complete async hybrid_search)
- [ ] 4. Dependencies: Update `Application/requirements.txt`
- [ ] 5. Test: `Application/Scripts/perf_test.py` → new baseline (target mean <25s, std<2s)
- [ ] 6. Deploy: `uvicorn Application.API.Main_fixed:app --reload`

## Phase 2: Advanced (~20% further)
- [ ] LLM Batching in Author_agent.py
- [ ] FastAPI-Cache in Main_fixed.py
- [ ] Async Playwright in scraper_core_fixed.py

## Phase 3: Monitoring
- [ ] Prometheus integration

**Progress: 1/6 Phase 1**  
**Next: Workflow async (syllabus_workflow.py)**
- [ ] 2. Workflow Async: Edit `Application/Workflows/syllabus_workflow.py` (async planner/assemble nodes, parallel scrape)
- [ ] 3. TripleDB Async: Edit `Application/Ports/triple_db_manager.py` (complete async hybrid_search)
- [ ] 4. Dependencies: Update `Application/requirements.txt`
- [ ] 5. Test: `Application/Scripts/perf_test.py` → new baseline (target mean <25s, std<2s)
- [ ] 6. Deploy: `uvicorn Application.API.Main_fixed:app --reload`

## Phase 2: Advanced (~20% further)
- [ ] LLM Batching in Author_agent.py
- [ ] FastAPI-Cache in Main_fixed.py
- [ ] Async Playwright in scraper_core_fixed.py

## Phase 3: Monitoring
- [ ] Prometheus integration

**Progress: 0/6 Phase 1**  
**Next: DB indexes (lowest risk/high impact)**
