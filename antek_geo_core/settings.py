"""Runtime settings for antek-geo-core — env-driven, no repo config coupling.

Both geo-slab and geo-prospecting set these via their own .env; the core only
reads os.environ so it stays a pure library with no import-time dependency on
either repo's config module.
"""
from __future__ import annotations

import os


def _bool(v: str) -> bool:
    return str(v).strip().lower() not in ("0", "false", "no", "")


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Attach OpenRouter's web plugin so chat models answer from live search
# (matches real ChatGPT/Gemini behaviour). Toggle GEO_WEB_SEARCH=0 to disable.
WEB_SEARCH = _bool(os.getenv("GEO_WEB_SEARCH", "1"))
WEB_SEARCH_MAX_RESULTS = int(os.getenv("GEO_WEB_SEARCH_MAX", "5"))

# Referer/title sent on OpenRouter calls (analytics only).
HTTP_REFERER = os.getenv("GEO_HTTP_REFERER", "https://antekautomation.com")
X_TITLE = os.getenv("GEO_X_TITLE", "antek-geo-core")
