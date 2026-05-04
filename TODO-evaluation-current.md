# Current Evaluation Run — TODO

## Phase 1: Execute Test Suite
- [ ] Run unit tests (`pytest Application/Tests/ -v --tb=short -m "not integration"`)
- [ ] Run integration tests (`pytest Application/Tests/ -v --tb=short -m integration`)
- [ ] Collect raw pass/fail/error counts

## Phase 2: Performance Benchmark
- [ ] Check if API server is reachable
- [ ] Run `perf_test_fixed.py` if feasible
- [ ] Record latency & 5-factor scores

## Phase 3: Failure Analysis & Quick Fixes
- [ ] Read failing tests to categorize root causes
- [ ] Apply trivial fixes (assertion mismatches, outdated mocks)
- [ ] Re-run affected tests to verify

## Phase 4: Report Update
- [ ] Refresh `EVALUATION_REPORT.md` with new metrics
- [ ] Update `TODO-evaluation.md` with completion status
- [ ] Update this TODO

