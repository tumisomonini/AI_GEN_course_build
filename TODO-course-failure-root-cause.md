# Course Generation Failure - Root Cause Fix
## Status: In Progress (Approved Plan)

**Root Cause Confirmed**: Infrastructure not running (Docker Postgres/Neo4j + FastAPI server) OR missing OPENROUTER_API_KEY → LLM/workflow fails → status="failed".

## Step-by-Step Execution Plan

### 1. [ ] Diagnose Current Status (Run Commands)
- Check Docker: `docker ps`
- Check Server: `ps aux | grep uvicorn`
- Check DB Connect: Test PostgresRepo init

### 2. [ ] Start Infrastructure
- Docker: `cd Application/Docker &amp;&amp; docker-compose up -d`
- Server: `./run_dev.sh` OR `PYTHONPATH=. uvicorn Application.API.Main:app --reload --port 8000`

### 3. [ ] Verify API Key (.env)
- Add `OPENROUTER_API_KEY=sk-or-v1-...` (signup at openrouter.ai)
- Test agents: curl health endpoint

### 4. [ ] Test Generation Flow
- Run `python Application/Tests/test_frontend_api_interactivity.py`
- UI: http://localhost:8000/pages/test_interface.html → Generate course
- Poll `/courses/{id}/status` → expect "completed"

### 5. [x] Query DB for Past Failures
- Use repo.get_latest_error(course_id)

### 6. [ ] Confirm Fix
- End-to-end: Template → Approve → Full gen → Download

**Next Action**: Execute Step 1 diagnostics.

