"""Google AI Overview probe — SerpApi-first (no Apify dependency).

CANONICAL = geo-prospecting/src/visibility/probes.py. Crucial detail: when the
main SERP only returns a page_token (Google defers AI-Overview generation, the
common case), follow it with a second engine=google_ai_overview request — else
most real AI Overviews come back NO_AI_OVERVIEW.

Returns the AI Overview text if present, else organic titles prefixed with
NO_AI_OVERVIEW so downstream scoring still has signal. "ERROR" on failure.
"""
from __future__ import annotations

import time

import requests

from . import settings


def serpapi_ai_overview(query: str, gl: str = "gb", location: str = "United Kingdom",
                        api_key: str | None = None) -> str:
    api_key = api_key or settings.SERPAPI_KEY
    if not api_key:
        raise RuntimeError("SERPAPI_KEY is not set.")
    for attempt in range(3):
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={"q": query, "location": location, "gl": gl, "hl": "en",
                        "api_key": api_key},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            ai = data.get("ai_overview")
            token = ai.get("page_token") if isinstance(ai, dict) else None
            if token and not (isinstance(ai, dict) and ai.get("text_blocks")):
                resp2 = requests.get(
                    "https://serpapi.com/search",
                    params={"engine": "google_ai_overview", "page_token": token,
                            "api_key": api_key},
                    timeout=30,
                )
                resp2.raise_for_status()
                data2 = resp2.json()
                if data2.get("ai_overview"):
                    data = data2
            return _extract_ai_overview(data)
        except Exception:  # noqa: BLE001
            if attempt == 2:
                return "ERROR"
            time.sleep(2 ** attempt)
    return "ERROR"


def _extract_ai_overview(data: dict) -> str:
    """AI Overview block text if present, else organic titles (NO_AI_OVERVIEW
    prefix) so scoring still has signal."""
    ai = data.get("ai_overview")
    if isinstance(ai, dict):
        chunks = []
        for block in ai.get("text_blocks", []) or []:
            if block.get("snippet"):
                chunks.append(block["snippet"])
            for item in block.get("list", []) or []:
                if item.get("snippet"):
                    chunks.append(item["snippet"])
        for ref in ai.get("references", []) or []:
            if ref.get("title"):
                chunks.append(ref["title"])
        if chunks:
            return "\n".join(chunks)
    titles = [r.get("title", "") for r in data.get("organic_results", [])[:8]]
    return "NO_AI_OVERVIEW\n" + "\n".join(t for t in titles if t)
