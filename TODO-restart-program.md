# Restart Program - Steps Tracker

## Status: In Progress

**Plan Steps:**
1. [x] Edit `Application/API/dependencies.py` - Add `sanitize_neo4j_uri` function  
2. [x] Kill port 8000 processes  
3. [x] Rerun `./run_dev.sh`  
4. [x] Verify server & health: `curl http://localhost:8000/health` (degraded - DBs down)
5. [x] Note: Start Docker Desktop for full DBs (`open -a Docker` or `brew services start docker`; then `docker compose -f Application/Docker/docker-compose.yml up -d`)

**Notes:**  
- Docker daemon down - degraded mode until started  
- Server live at http://localhost:8000 → /Pages/dashboard.html
