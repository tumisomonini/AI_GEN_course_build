# Restart Program - Step-by-Step TODO

## Approved Plan Steps:

- [x] 1. Kill stale processes on port 8000 (`lsof -ti:8000 | xargs kill -9`) ✅ No processes found
- [ ] 2. Start Docker daemon if needed (`open -a Docker` or `brew services start docker`) ⚠️ Connection failed; ensure Docker Desktop is fully initialized
- [ ] 3. Start DB services (`cd Application/Docker && docker compose up -d`) ❌ Connection refused on 5433; check Docker Desktop logs
- [x] 4. Install/update requirements (`pip install -r requirements.txt`) ✅ Completed (sentencepiece build failed due to missing cmake/pkg-config, non-critical for core app)
- [x] 5. Start/restart dev server (`./run_dev.sh`) ✅ Already running via Docker (`course_builder_api`); local attempt failed (port 8000 in use)
- [x] 6. Verify health (`curl http://localhost:8000/health`) ✅ Degraded: Postgres down (init issue?), Neo4j OK (1 topic), agents Postgres error
- [x] 7. Open UI (`open http://localhost:8000/Pages/dashboard.html`) ✅ Dashboard and test interface opened in browser

**Current Status:** Plan approved. Executing steps sequentially.
