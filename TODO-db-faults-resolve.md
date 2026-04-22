# DB Faults Resolution TODO
Status: 🔄 In Progress (BLACKBOXAI) - Plan Approved

## Breakdown Steps (Sequential)

### 1. **✅ Create .env.example** (env standardization)
   - Local defaults: POSTGRES_PORT=5433, NEO4J_URI=bolt://localhost:7687, secrets placeholders.

### 2. **Edit docker-compose.yml** (secrets/redis)
   - Use ${POSTGRES_PASSWORD:-password123}, ${NEO4J_PASSWORD:-password}.
   - Comment redis (unused).

### 3. **Edit dependencies.py** (vector fallback + cleanup)
   - get_vector_store(): Astra → LocalVectorStore → PostgresVectorRepo.
   - Add session cleanup func.

### 4. **Edit schema.sql** (dupe note)
   - Add comment on idempotency.

### 5. **Edit start_dbs.py** (auto-clean/populate)
   - Call repo.cleanup_expired_sessions(), populate_all_dbs.py.

### 6. **Test & Verify**
   - docker compose up -d && python start_dbs.py --populate
   - curl /health (vector fallback shows)
   - pytest test_db_health.py

### 7. **✅ COMPLETE** (all faults resolved)
