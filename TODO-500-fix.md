# Fix 500 Server Error - Progress Tracker

**Goal**: Diagnose and resolve generic 500 errors from unhandled exceptions (likely /syllabus/generate).

**Current Status**: Planning → Implementation

## Steps:
 1. [x] Gather info: Analyzed files.
 2. [x] Health degraded (Neo4j DNS fail). Generate: TypeError None callable (workflow None from import fail).
 3. Restart server clean.
3. [ ] Add error middleware to Main.py for detailed tracebacks.
4. [ ] Improve syllabus.py except blocks (specific exceptions).
5. [ ] Add env validation in lifespan.
6. [ ] Test: Start server `cd Application && uvicorn API.Main:app --reload`
7. [ ] Test health `/health`, then `/syllabus/generate`.
8. [ ] Fix any new Import/DB/agent errors.
9. [ ] Add logging with structlog or rich.
10. [ ] pytest Application/Tests/test_api.py

**Suspects**:
- Missing ASTRA_DB_APPLICATION_TOKEN → ValueError.
- No LLM keys → AuthorAgent fails.
- Postgres/Neo4j not running.
- Workflow timeout in parallel author generation.

**Estimated time**: 15 mins

