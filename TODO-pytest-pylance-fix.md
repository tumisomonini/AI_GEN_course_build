# Pytest-Pylance Fix Progress

## Steps:
- [x] 1. Create this TODO file\n- [x] 2. Edit `Application/Tests/test_reviewer_agent.py` to remove invalid `await` on sync `route_query`
- [x] 3. Test with `pytest Application/Tests/test_reviewer_agent.py -v` (Note: ImportError due to pytest module discovery from rootdir; type fix confirmed, tests collect cleanly with PYTHONPATH)
- [x] 4. Mark complete and attempt_completion

