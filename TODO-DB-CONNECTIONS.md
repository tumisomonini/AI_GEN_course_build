# TODO: Solidify Database Connections Before Operation

Status: 🔄 In Progress (BLACKBOXAI)

## Plan Steps

### 1. ✅ Create this TODO.md [DONE]

### 2. ✅ Add universal DB health checker in dependencies.py [DONE]
- New `check_all_dbs()` w/ @retry
- Critical: pg+neo4j fail→raise, astra optional

### 3. ✅ Enhance individual inits [DONE]
 - deps.py: @retry on PostgresRepo + schema
 - AstraVectorStore: _test_connection() post-collection
 - Graceful degradation

### 4. ✅ Update Main.py lifespan [DONE]
- check_all_dbs() call in startup
- Continues degraded if non-critical fail

### 5. ✅ Create Application/Scripts/start_dbs.py [DONE]
 - docker/local polls, init_astra, populate

### 6. ✅ Robustify /health [DONE]
 - 3-try retries on all pings

### 7. ✅ Add test_db_health.py [DONE]
 - pytest for check_all_dbs + singletons

### 8. ✅ COMPLETE
- All DB connections solid w/ retries/healthchecks
- Startup blocks if critical down
- Run: cd Application/Docker && docker-compose up -d && cd ../.. && python Application/Scripts/start_dbs.py --populate && uvicorn Application.API.Main:app --reload && curl localhost:8000/health

## Testing Commands
```bash
docker-compose up -d  # DBs first
python Application/Scripts/start_dbs.py  # Dev check
uvicorn Application.API.Main:app --reload
curl http://localhost:8000/health
pytest Application/Tests/
```

## Notes
- Prioritize dev non-Docker (local fallbacks)
- Docker already strong (healthchecks/depends_on)
- Astra: Graceful if no token

