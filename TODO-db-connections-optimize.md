# Resolve Database Connections & Upserts Bottleneck (Astra_repo.py)

Status: 🔄 In Progress

## Steps

- [ ] 1. Create this TODO.md file ✅
- [x] 3. Add batch size limits and use faster bulk upsert (add_texts + 50-batch, fixed syntax) ✅
- [ ] 4. Optimize Postgres logging in syllabus_workflow.py (batch/async)
- [ ] 5. Test with scrape_syllabus.py & measure time improvement
- [ ] 6. Run perf_test.py if relevant
- [ ] 7. Verify no regressions in workflows/tests
- [ ] 8. Update TODO.md as complete & attempt_completion

### Target: Reduce upsert time by 1-2s (3-5% overall)

### Files to edit:
- Application/Ports/Astra_repo.py
- Application/Workflows/syllabus_workflow.py

