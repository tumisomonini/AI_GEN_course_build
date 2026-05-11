"""Quick local smoke test for Chroma.

This file lives under `Application/Ports/` and may be picked up by pytest
collection. It should not hard-fail test runs when the repo is imported
without proper PYTHONPATH.

Run manually with:
  python -m Application.Ports.chroma_quick_test
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    # Ensure repo root is on sys.path when run from arbitrary working dirs.
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from Application.Ports.Chroma_repo import ChromaRepo

    r = ChromaRepo("quick_test_collection")

    texts = ["hello world", "goodbye world", "python programming"]
    metas = [{"course": "x"}, {"course": "x"}, {"course": "y"}]
    r.upsert_syllabus_chunks(texts, metas)

    res = r.similarity_search("hello", k=2, min_score=0.0)
    print(res)


if __name__ == "__main__":
    main()


