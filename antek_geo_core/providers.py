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
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

# Real OpenAI model used as the direct fallback for any "openai/*" OpenRouter
# model id when OpenRouter's upstream provider 400s (e.g. Azure outage,
# 2026-08). Same 5.2 generation as OpenRouter's "openai/gpt-5.2-chat" — the
# "-chat" chat-completions variant is deprecated direct-from-OpenAI on some
# accounts, but the base "gpt-5.2" model works via the Responses API with
# the web_search_preview tool attached, giving genuine live-grounded search
# (not a downgrade substitute like gpt-4o-search-preview).
OPENAI_FALLBACK_MODEL = "gpt-5.2"


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


def _query_openai_direct(prompt: str) -> Optional[dict]:
    """Direct OpenAI call via the Responses API, bypassing OpenRouter
    entirely. Only used as a fallback (see query_openrouter_full) — no
    cost/usage accounting from OpenRouter here, so cost_usd is left at 0.0
    and must be estimated upstream if needed."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        resp = requests.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_FALLBACK_MODEL,
                "input": prompt,
                "tools": [{"type": "web_search_preview"}],
            },
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        text = ""
        for item in data.get("output") or []:
            if item.get("type") == "message":
                for c in item.get("content") or []:
                    if c.get("type") == "output_text":
                        text += c.get("text", "")
        if not text:
            raise ValueError("no message output in Responses API result")
        usage = data.get("usage") or {}
        return {
            "text": text,
            "cost_usd": 0.0,
            "tokens": usage.get("total_tokens", 0),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[OpenAI-direct/{OPENAI_FALLBACK_MODEL}] error: {exc}", file=sys.stderr)
        return None


def query_openrouter_full(prompt: str, model: str, api_key: str | None = None) -> Optional[dict]:
    """Call OpenRouter with usage accounting. Returns {text, cost_usd, tokens}
    or None on error.

    Automatic fallback: if the model is an "openai/*" OpenRouter id and the
    OpenRouter call fails (e.g. an upstream provider outage — confirmed
    2026-08 as an Azure "BadRequestForDependentService" that persisted across
    retries and payload variants, not a request problem), retries once via a
    direct OpenAI call (see _query_openai_direct) rather than silently
    returning None. Requires OPENAI_API_KEY; if unset, behaves exactly as
    before (no regression) — this must be automatic, not a manual re-run,
    per standing policy that visibility-scan failures can't rely on someone
    noticing and intervening by hand."""
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
        if model.lower().startswith("openai/") and settings.OPENAI_API_KEY:
            print(f"[OpenRouter/{model}] falling back to direct OpenAI "
                  f"({OPENAI_FALLBACK_MODEL})", file=sys.stderr)
            return _query_openai_direct(prompt)
        return None
