from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LLMResult:
    """Output of triage."""

    selected_indices: List[int]
    raw_response: Optional[str] = None


def _llm_enabled_from_env() -> bool:
    # Enable by explicitly setting a provider + key.
    return bool(os.getenv("LLM_TRIAGE_ENABLED", "").strip().lower() in {"1", "true", "yes"})


def triage_results(
    *,
    course_title: str,
    results: List[Dict[str, Any]],
    select_top_k: int = 2,
    timeout_s: int = 15,
) -> LLMResult:
    """Return indices of results to fully scrape.

    This implementation is intentionally defensive:
    - If no provider is configured, it returns the first k indices.
    - If provider import/key is missing, it falls back to first k indices.

    Supported env vars (optional):
    - LLM_TRIAGE_PROVIDER = "openrouter" | "openai" (default: openrouter)
    - OPENROUTER_API_KEY / OPENAI_API_KEY
    - OPENROUTER_MODEL / OPENAI_MODEL (defaults provided)

    For latency we keep prompt small and request a strict JSON object.
    """

    if not results:
        return LLMResult(selected_indices=[])

    default_indices = list(range(min(select_top_k, len(results))))

    if not _llm_enabled_from_env():
        return LLMResult(selected_indices=default_indices)

    provider = os.getenv("LLM_TRIAGE_PROVIDER", "openrouter").strip().lower()

    # -------- OpenRouter (preferred in this repo) --------
    if provider in {"openrouter", "open_router", "openrouter.ai"}:
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        if not api_key:
            return LLMResult(selected_indices=default_indices)

        try:
            from openai import OpenAI  # type: ignore

            client = OpenAI(
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                api_key=api_key,
            )

            # Build minimal candidate list.
            candidates = []
            for i, r in enumerate(results):
                candidates.append(
                    {
                        "index": i,
                        "title": (r.get("title") or "").strip(),
                        "url": (r.get("href") or "").strip(),
                    }
                )

            prompt = (
                "You are an assistant helping select the most relevant course syllabus pages. "
                "Given a course title and a list of search results (title+url), choose which results "
                "most likely contain a real syllabus or curriculum outline with topics/modules/weeks. "
                "Return ONLY valid JSON like {\"selected_indices\":[0,2]} with exactly select_top_k indices."
            )

            user_payload = {
                "course_title": course_title,
                "select_top_k": select_top_k,
                "results": candidates,
            }

            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(user_payload)},
                ],
                temperature=0,
                timeout=timeout_s,
            )

            content = (resp.choices[0].message.content or "").strip()
            data = json.loads(content)
            selected = data.get("selected_indices", default_indices)

            # sanitize
            sanitized: List[int] = []
            for x in selected:
                try:
                    i = int(x)
                except Exception:
                    continue
                if 0 <= i < len(results) and i not in sanitized:
                    sanitized.append(i)
                if len(sanitized) >= select_top_k:
                    break

            if not sanitized:
                sanitized = default_indices
            return LLMResult(selected_indices=sanitized, raw_response=content)

        except Exception:
            return LLMResult(selected_indices=default_indices)

    # -------- Unknown provider: fallback --------
    return LLMResult(selected_indices=default_indices)

