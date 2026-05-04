# DB Issues Resolution Plan - Tracking Progress

## Approved Plan Steps (Proceed Sequentially)

### 1. [✅] Update requirements.txt
   - Add SQLAlchemy, alembic[psycopg2]
   - pip install -r requirements.txt

### 2. [ ] Setup Alembic migrations
   - Create migrations/ dir with env.py, script.py.mako
   - alembic init migrations
   - Initial migration from schema.sql
   - Configure alembic.ini

### 3. [ ] Refactor postgres_repo.py to SQLAlchemy ORM
   - Define Base/models for 15 tables
   - Convert all cur.execute to session.query/add/commit
   - Remove init_schema()

### 4. [ ] Update Ports/postgres_repo.py adapter
   - Delegate to ORM repo

### 5. [ ] Refactor triple_db_manager.py for DI
   - Constructor takes pg_repo, neo_repo, astra_repo
   - Remove singleton/direct instantiation

### 6. [ ] Update dependencies.py
   - get_triple_db_manager() uses Depends(get_postgres_repo, etc.)

### 7. [ ] Update Scripts/init_postgres.py
   - Use alembic upgrade head

### 8. [ ] Update dependent files/tests
   - Fix method signatures if changed
   - pytest tests

### 9. [ ] Verify
   - alembic upgrade head
   - Create course/run via TripleDBManager
   - Check no raw SQL regressions

**Current Progress: Starting Step 1**

**Notes:** Focus Postgres first, Neo4j Cypher later. Keep psycopg2 compat. Backup schema.sql.

