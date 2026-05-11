_# Hybrid retrieval implementation TODO

## Goal
Add hybrid retrieval to the syllabus retrieval layer:
- Dense: existing Chroma cosine similarity
- Sparse/lexical: add local keyword/BM25 index
- Fusion: score-weighted merge of dense+sparse results

## Steps
1. Add a lexical index implementation (FTS5/keyword) under `Application/Infrastructure/retrieval/`.
2. Extend the adapter that owns retrieval (`Application/Ports/Chroma_repo.py`) with a new method `hybrid_search(...)`.
3. Keep `similarity_search()` unchanged.
4. Wire selection logic via env var `RETRIEVAL_MODE=dense|hybrid`.
5. Update the retrieval call site used for faithfulness/RAG to call `hybrid_search()` when enabled.
6. Add tests for hybrid fusion behavior.
7. Run `pytest`.

