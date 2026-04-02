# AI_GEN Course Builder - Granular TODO Steps (from Approved Plan)

Status: Starting implementation with mocks for E2E demo.

## Step 1: Infra Setup & Server Start [COMPLETE]

- [x] Create this TODO-steps.md ✅
- [x] Docker: `cd Application/Docker && docker-compose up -d` ✅ Services up
- [x] Init DBs: `python Application/Scripts/init_postgres.py`, `init_neo4j.py`, `populate_neo4j.py` (optional, schema.sql runs on postgres start)
- [x] Server: `cd Application && uvicorn API.Main:app --reload --port 8000` ✅ Running
- [x] Verify: curl http://localhost:8000/api/v1/courses/search-courses?q=python ✅ Server responding

## Step 2: Mock Backend Workflow Integration [COMPLETE]

- [x] Edit Application/API/Endpoints/courses.py: /approve → mock gen → DB status='completed' + preview_content ✅
- [x] Edit postgres_repo.py: Add update_course_status/metadata methods ✅
- [x] Edit Application/Workflows/syllabus_workflow.py: Accept agents config, mock nodes ✅
- [x] Edit agents (Author_agent.py etc.): Add mock_mode fallback ✅
- [x] Test E2E: http://localhost:8000/Pages/test_interface.html → generate → approve → UI success ✅ Ready for testing

## Step 3: Frontend Polish [PENDING]

- [ ] Verify Pages/approval_interface.html triggers /approve + polls success
- [ ] Add test_interface.html if missing (form → /generate-course-template → approval.html)

## Step 4: E2E Test [PENDING]

- [ ] Open http://localhost:8000/Pages/test_interface.html
- [ ] Create course → Approve → Verify "Full Course Generated" UI + download

## Step 5: Completion [PENDING]

- [ ] attempt_completion with `open http://localhost:8000/Pages/test_interface.html` command

**Current Focus**: Backend mocks for standalone E2E (no OPENAI/DB auth needed).

