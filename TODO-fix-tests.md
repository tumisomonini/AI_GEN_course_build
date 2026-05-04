# Fix Failing Tests - TODO

## Steps

- [ ] **Step 1**: Fix `models.py` - Add `UniqueConstraint` import to unblock all imports
- [ ] **Step 2**: Fix `postgres_repo.py` - Add `ON CONFLICT DO UPDATE` to `create_course_from_template`
- [ ] **Step 3**: Fix `test_postgres_repo.py` - Use unique titles to avoid collisions
- [ ] **Step 4**: Fix `test_db_health.py` - Skip tests gracefully when DBs not available
- [ ] **Step 5**: Run tests, then fix `test_syllabus_workflow.py` based on actual errors
- [ ] **Step 6**: Final verification run

