# Restart Program - Current Steps

## Plan Steps:
1. [x] Docker services: \`docker compose -f Application/Docker/docker-compose.yml up -d\`
2. [x] Kill port 8000: \`lsof -ti:8000 | xargs kill -9 2>/dev/null || true\`
4. [ ] Start dev server: \`cd Application && ./run_dev.sh\`
4. [ ] Verify: \`curl http://localhost:8000/health\`

**Status:** 2/4 complete. Starting API server next.

## Logs:
```
