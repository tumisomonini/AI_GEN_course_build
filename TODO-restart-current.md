# Restart Program - Current Steps

## Plan Steps:
1. [ ] Docker services: \`docker compose -f Application/Docker/docker-compose.yml up -d\`
2. [ ] Kill port 8000: \`lsof -ti:8000 | xargs kill -9 2>/dev/null || true\`
3. [ ] Start dev server: \`cd Application && ./run_dev.sh\`
4. [ ] Verify: \`curl http://localhost:8000/health\`

**Status:** 0/4 complete. Logs below.

## Logs:
```

