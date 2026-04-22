# Resolve Astra Timeout + Deps + Live Server [BLACKBOXAI]
Status: 🔄 In Progress

## Breakdown from Approved Plan

### 1. Dependencies Fix
- [✅] Update requirements.txt: Add `langchain-astradb>=0.2.0`
- [✅] Install: `pip install -r requirements.txt --upgrade`

### 2. Embedder Timeout Production Fix
- [✅] Pre-cache HF model: Execute command to download 'all-MiniLM-L6-v2'
- [✅] Edit Application/Ports/Astra_repo.py: Add timeout to HuggingFaceEmbeddings, lazy init if possible
- [✅] Edit Application/API/dependencies.py: Lighter test_astra() (no upsert/search), longer retries, fallback to local vector store
- [✅] Edit Application/API/Main.py: Optimize /health Astra check to lighter test

### 3. Full Live Server + E2E Tests
- [✅] Start DBs: `cd Application/Docker && docker-compose up -d postgres neo4j`
- [✅] Populate data: `python Application/Scripts/populate_all_dbs.py`
- [✅] Run uvicorn: `uvicorn Application.API.Main:app --reload --port 8000`
- [ ] Test health: `curl http://localhost:8000/health` (no timeout)
- [ ] Test scrape/RAG: `curl -X POST http://localhost:8000/syllabus/scrape -H "Content-Type: application/json" -d '{"url": "https://example.com/syllabus.pdf"}'`
- [ ] ✅ COMPLETE: Production-ready, no timeouts, full RAG E2E

## Commands Preview
```bash
pip install -r requirements.txt --upgrade
# Cache model
cd Application/Docker && docker-compose up -d
python Application/Scripts/populate_all_dbs.py
uvicorn Application.API.Main:app --reload --port 8000
curl http://localhost:8000/health | jq
```

**Next: Dependencies → Embedder fixes → Server live.**

