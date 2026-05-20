# Next fix needed: `test_course_creation.py`

`pytest.ini` sets `testpaths = Application/Tests`, but the failing `test_course_creation.py` at repo root is being collected anyway (so it must match `python_files = test_*.py`).

That file currently:
- imports `PostgresORMRepository`
- instantiates it at import time: `repo = PostgresORMRepository()`
- runs DB operations in a top-level `try:` block

This causes pytest collection to fail with OperationalError.

Plan:
1. Replace root `test_course_creation.py` with a proper pytest test function.
2. Add a reachability gate (TCP check) and skip on connection refusal / OperationalError.
3. Ensure the module has no DB calls during import time.
