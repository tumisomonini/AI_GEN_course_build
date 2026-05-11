"""Compatibility shim for test monkeypatch paths.

Tests historically monkeypatch:
- Application.Infrastructure.Scraper.scraper_core.Scraper
- Application.Infrastructure.Scraper.scraper_core.DDGS

The implementation lives in scraper_core_fixed.py.
This module re-exports the expected symbols so monkeypatching works.
"""

from __future__ import annotations

from Application.Infrastructure.Scraper.scraper_core_fixed import Scraper  # noqa: F401

# Re-export names referenced by tests.
try:
    from Application.Infrastructure.Scraper.scraper_core_fixed import DDGS  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover
    DDGS = None  # type: ignore


