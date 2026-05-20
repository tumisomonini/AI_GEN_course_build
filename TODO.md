# TODO

## DB + workflow reliability fixes
- [x] Modify `TripleDBManager` to degrade gracefully (no hard ValueError when Postgres/Neo4j missing)
- [x] Add hard stop for LangGraph reviewer→author loop via `review_iterations` / `review_iteration_limit`
- [ ] Re-run pytest to confirm the DB-health failures are resolved and recursion errors are gone

