"""Clear local caches used by the FastAPI app.

This project uses a persisted Chroma directory as a dev/test vector-store.
Clearing it removes the local vector cache.

Usage:
  python Application/Scripts/clear_fastapi_cache.py

Environment variables:
  CHROMA_PERSIST_DIR   Base folder where `chroma_db/` lives.
                        Default: current working directory.
  CHROMA_DB_DIR        Override full path to chroma_db dir.
                        If set, CHROMA_PERSIST_DIR is ignored.
  DRY_RUN              If '1', only prints what would be removed.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def _resolve_chroma_db_dir() -> Path:
    override = os.getenv("CHROMA_DB_DIR")
    if override:
        return Path(override).expanduser().resolve()

    persist_dir = Path(os.getenv("CHROMA_PERSIST_DIR", str(Path.cwd()))).expanduser().resolve()
    return (persist_dir / "chroma_db").resolve()


def clear_chroma_cache(*, dry_run: bool) -> None:
    chroma_db_dir = _resolve_chroma_db_dir()

    if not chroma_db_dir.exists():
        print(f"Chroma cache dir not found (nothing to clear): {chroma_db_dir}")
        return

    if dry_run:
        print(f"[DRY_RUN] Would remove: {chroma_db_dir}")
        return

    shutil.rmtree(chroma_db_dir)
    print(f"✅ Cleared Chroma cache: {chroma_db_dir}")


def main() -> None:
    dry_run = os.getenv("DRY_RUN") == "1"

    print("Clearing FastAPI-related local caches (vector-store cache)...")
    clear_chroma_cache(dry_run=dry_run)
    print("Done.")


if __name__ == "__main__":
    main()

