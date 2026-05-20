from __future__ import annotations

import os
from typing import Any, Dict, List


def serpapi_search(query: str, *, max_results: int = 5, country: str = "us") -> List[Dict[str, Any]]:
    """Serpapi-based search returning result dicts compatible with scraper_core_fixed.

    Output items contain at least:
      - href (URL)
      - title

    Requires:
      - SERPAPI_API_KEY
      - serpapi package installed
    """

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return []

    try:
        from serpapi import GoogleSearch  # type: ignore
    except Exception as e:
        raise RuntimeError("serpapi package not installed") from e

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": max_results,
        "hl": "en",
        "gl": country,
    }

    search = GoogleSearch(params)
    data = search.get_dict()

    results: List[Dict[str, Any]] = []

    organic = data.get("organic_results") or []
    for item in organic[:max_results]:
        # Serpapi organic item fields typically include: title, link
        href = item.get("link") or item.get("url") or ""
        title = item.get("title") or ""
        if not href and isinstance(item.get("serpapi_link"), str):
            href = item["serpapi_link"]

        if href:
            results.append({"href": href, "title": title, "snippet": item.get("snippet")})

    return results

