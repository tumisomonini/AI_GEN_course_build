# WorkflowManager Enhancement TODO

## Steps (Approved Plan Implementation):
- [✅] 1. Create this TODO.md
- [✅] 2. Edit `workflow_manager.py`: Add config to init(), improve Neo4j/Astra health checks (try-connect or configurable skip), add `get_factory(name)` for raw workflows, add `is_healthy()` property.
- [ ] 3. Edit `syllabus_workflow.py`: Graceful None repo log in upsert, add asyncio.wait_for(30s) to key executors.
- [ ] 4. Edit `__init__.py`: Ensure \"manager\" in __all__.
- [ ] 5. Test: `cd Application && pytest -v Workflows/` (confirm no regressions).
- [ ] 6. Smoke test: `python Application/Scripts/workflow_init.py`.
- [ ] 7. Update this TODO.md with completions.
- [ ] 8. attempt_completion.

**Status**: Starting edits...

