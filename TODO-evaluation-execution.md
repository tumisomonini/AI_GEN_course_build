# Evaluation Execution Tracker

## Phase 1: Fix Critical Code Issues
- [ ] Fix `Domain/syllabus.py` — add missing `reviewer_semantic_avg` and `semantic_pass_rate`
- [ ] Fix `Application/Workflows/syllabus_workflow.py` — stop closing singleton pool
- [ ] Fix `Application/API/dependencies.py` — handle `DuplicateTable` gracefully
- [ ] Fix `Application/Infrastructure/relationalDB/postgres_repo.py` — ensure unique constraint for ON CONFLICT
- [ ] Fix `Application/Tests/test_postgres_repo.py` — add cleanup fixture
- [ ] Fix `Application/Tests/test_db_health.py` — relax assertions

## Phase 2: Execute Test Suite
- [ ] Run unit tests (`pytest Application/Tests/ -v --tb=short -m "not integration"`)
- [ ] Run integration tests (`pytest Application/Tests/ -v --tb=short -m integration`)
- [ ] Collect results

## Phase 3: Performance Benchmark
- [ ] Check API health
- [ ] Run `perf_test_fixed.py`
- [ ] Record metrics

## Phase 4: Update Reports
- [ ] Refresh `EVALUATION_REPORT.md`
- [ ] Update `TODO-evaluation.md`
- [ ] Update `TODO-evaluation-current.md`

