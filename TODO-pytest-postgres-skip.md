# Pytest Postgres Collection Failures

## Problem
Some test files at repo root (`test_course_creation.py`, `test_raw_course_creation.py`) execute DB connections at import time or during collection. In environments where Postgres is unreachable or refuses connections (e.g. "too many clients already"), pytest fails during collection.

## Fix approach
- Convert these root-level scripts into proper pytest tests.
- Add a lightweight DB reachability gate and handle “connection refused / too many clients” by `pytest.skip()`.

## Current status
- ✅ `test_raw_course_creation.py` converted + now skips gracefully.
- ⛔ `test_course_creation.py` still fails during collection (import-time repository initialization).

## Next step
- Patch `test_course_creation.py` to match the same skip strategy.

