# RAG System Full Testing - Steps (Approved Plan)

## Prerequisites ✓

- [x] Docker services running: Postgres/Neo4j/Redis up ✅
- [x] Baseline pytest: `pytest Application/Tests/ -v` ✓ (28/31 PASS, 2 minor API fails)
- [x] Env vars: NEO4J/Astra/OpenRouter set ✅

 ## 1. Test Data Setup ✓

 - [x] Create `Application/Scripts/test_data_loader.py` (scrape + Astra upsert + Neo4j topics)
 - [x] Run loader: `cd Application/Scripts && python test_data_loader.py --course \"Intro to Machine Learning\"` ✅

 ## 2. Integration Tests ✓

 - [x] Create `Application/Tests/test_rag_integration.py` (API RAG flow) ✅
 - [x] Run: `pytest Application/Tests/test_rag_integration.py -v` ✅ (Now includes accuracy checks)

## 3. Enhance Existing Tests

- [ ] Edit `Application/Tests/test_api.py`: Add content validation to `test_generate_syllabus`
- [ ] Edit `Application/Tests/test_syllabus_workflow.py`: Add live agent test variant (opt)

## 4. Full Execution & Coverage

- [ ] Full pytest: `pytest --cov=Application --cov-report=term-missing`
- [ ] Start server: `cd Application && PYTHONPATH=. uvicorn API.Main:app --port 8000 --reload`
- [ ] Manual E2E: curl localhost:8000/syllabus/scrape + /generate, verify syllabus.docx created

## 5. Completion

- [ ] Update TODO-agent-workflow-tests.md, TODO-integration.md, TODO-backend-tests.md
- [ ] Coverage report >70% for RAG paths
- [ ] attempt_completion

**Current Progress:** 0/Steps complete. Starting prerequisites.
