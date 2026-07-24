"""OpenRouter call — cost-tracked. CANONICAL signature (geo-prospecting's):

    query_openrouter_full(prompt, model, api_key=None) -> {text, cost_usd, tokens}

NOTE: geo-slab's old signature was (prompt, api_key, model) — the arg-order
swap that caused silent drift. Migrating both repos to THIS order is step 1 of
the consolidation. geo-slab's thin per-model wrappers (query_openrouter_chatgpt
etc.) should call this.
"""
from __future__ import annotations

import sys
from typing import Optional

import requests

from . import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _payload(model: str, prompt: str) -> dict:
    """Chat body + OpenRouter web plugin for live-search grounding, except
    Perplexity/sonar which already searches natively."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.7,
        "usage": {"include": True},
    }
    m = model.lower()
    if settings.WEB_SEARCH and "perplexity" not in m and "sonar" not in m:
        body["plugins"] = [{"id": "web", "max_results": settings.WEB_SEARCH_MAX_RESULTS}]
    return body


def query_openrouter_full(prompt: str, model: str, api_key: str | None = None) -> Optional[dict]:
    """Call OpenRouter with usage accounting. Returns {text, cost_usd, tokens}
    or None on error."""
    api_key = api_key or settings.OPENROUTER_API_KEY
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": settings.HTTP_REFERER,
                "X-Title": settings.X_TITLE,
            },
            json=_payload(model, prompt),
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage") or {}
        return {
            "text": data["choices"][0]["message"]["content"],
            "cost_usd": float(usage.get("cost", 0.0) or 0.0),
            "tokens": usage.get("total_tokens", 0),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[OpenRouter/{model}] error: {exc}", file=sys.stderr)
        return None
