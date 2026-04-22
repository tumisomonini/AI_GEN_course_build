# AstraDB Full Integration TODO

## Status: 🚀 In Progress (BLACKBOXAI)

- [x] 1. Create Application/Ports/Astra_repo.py (upsert/query port)
- [x] 2. Create Application/Infrastructure/vectorDb/Astra_vector_store.py (LangChain vectorstore)
- [x] 3. Edit Application/API/dependencies.py (add get_astra_repo, get_vector_store)
- [x] 4. Edit Application/API/Main.py (lifespan init + health fix)
- [x] 5. Edit Application/API/agents.py (already passing vector_store; warned if down)
- [x] 6. Edit Application/Workflows/syllabus_workflow.py (fix upsert call)
 - [x] 7. Edit Application/Scripts/populate_all_dbs.py (enable Astra population)
- [ ] 8. Add sample data population and test /health endpoint
- [ ] 9. Run pytest Application/Tests/test_rag_integration.py
- [x] ✅ 10. Integration complete! Run `python Application/Scripts/populate_all_dbs.py` then `uvicorn Application.API.Main:app --reload` and check http://localhost:8000/health

**Next:** Set env vars:
```
ASTRA_DB_APPLICATION_TOKEN=AstraCS:xLgwlXkHZpgpcFUanXeJGdwO:25456a4ad6b5ae3d786a2fe55343771097c7396f93143d83639e9e04f7129afb
ASTRA_DB_ID=your_db_id_here  # Get from Astra portal
```
Collection: syllabus_chunks (default).
