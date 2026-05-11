# TODO - Pylance fix: syllabus_workflow.py attribute access

## Problem
Pylance reports: `Cannot access attribute "get" for class "str"` in `Application/Workflows/syllabus_workflow.py`.

## Root cause (likely)
One of the values iterated over (e.g., `raw_planned` / `state.syllabus` / `result[...]`) is typed too broadly (e.g., `List[Any]`) and Pylance infers an element could be a `str`, but code calls `.get(...)` on it.

## Fix plan
- Make the element access explicitly guard on `isinstance(x, dict)` before calling `.get(...)`.
- Where needed, introduce a small helper to normalize items into dicts or strings.
- Avoid calling `.get(...)` on values that might be `str`.

## Files affected
- `Application/Workflows/syllabus_workflow.py`

## Progress
- [ ] Apply code changes to satisfy static typing.
- [ ] Re-run mypy/Pylance checks (or at least ensure no further `.get` on possible `str`).

