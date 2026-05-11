# TODO: Improve AI Workflow (Multi-agent LangGraph pipeline)

## Step 1 — Provenance-first RAG (source chunk tracking)
- [ ] Update `Application/Agents/Author_agent.py` to return provenance:
  - exact retrieved chunk IDs (or deterministic indices) and chunk text used
  - include this in `Chapter` or via additional return structure
- [ ] Update `Application/Workflows/syllabus_workflow.py`:
  - extend `SyllabusState` usage to carry `chapter_sources` (per-topic)
  - pass the exact retrieved sources into `ReviewerAgent.evaluate_rag_faithfulness`
  - remove/bypass regex guessing of `[Source Chunk n]`
- [ ] Update `Application/Agents/Reviewer_agent.py` to accept and rely on provided `source_chunks` only.

## Step 2 — Multi-stage reviewer gate + regeneration budget
- [ ] Refactor `reviewer_node` into:
  - fast checks (substance/style/safety) first
  - LLM semantic critique second
  - RAG faithfulness check last
- [ ] Add regeneration loop:
  - allow 1 refinement pass when faithfulness fails
  - otherwise mark chapter as `needs_manual_review` (no silent pass/fail)

## Step 3 — Standardize workflow contracts/state
- [ ] Ensure all nodes agree on state field names and defaults.
- [ ] If needed, update `Domain/syllabus.py` (state model) to include provenance fields.

## Step 4 — Observability / structured logging
- [ ] Add structured JSON logs per node/topic:
  - node name, run_id, chapter title, retrieval strategy, chunk_count
  - reviewer decision fields (semantic_pass, faithfulness_score, hallucination count)

## Step 5 — Async boundaries + rate-limit aware concurrency
- [ ] Ensure blocking DB calls are offloaded from event loop inside async nodes.
- [ ] Add adaptive concurrency for `AuthorAgent.generate_multiple_chapters`.

## Step 6 — Workflow-level caching
- [ ] Add caches for:
  - scrape results
  - topic ordering by topic-set hash
  - retrieval chunks by (query,strategy,k)

## Step 7 — Tests + perf verification
- [ ] Update/extend tests:
  - reviewer receives real sources (no regex guessing)
  - regeneration triggers when faithfulness fails
- [ ] Run:
  - `pytest` (unit)
  - `perf_test_fixed.py` / `Application/Scripts/perf_test.py`


