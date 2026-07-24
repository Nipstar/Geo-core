"""Model routing + geo-targeting — single source of truth for both products.

These are the four consumer flagships a real prospect's customers actually get,
all via one OpenRouter key, plus Google AI Overview (probed via SerpApi). Slugs
verified against the OpenRouter models list; re-check here if a platform 404s.
"""
from __future__ import annotations

# The four chat engines probed for the free visibility check.
CHECK_MODELS: dict[str, str] = {
    "ChatGPT": "openai/gpt-5.2-chat",
    "Claude": "anthropic/claude-sonnet-5",
    "Gemini": "google/gemini-2.5-flash",
    "Perplexity": "perplexity/sonar",
}

# Google AI Overview is probed via SerpApi, not a chat model — the 5th signal.
AI_OVERVIEW_ENGINE = "ai_overview"
CHECK_ENGINES = list(CHECK_MODELS.keys()) + [AI_OVERVIEW_ENGINE]

# Cheap utility models (classification / enrichment) — used by callers, not the check.
UTILITY_MODELS = {
    "classify": "openai/gpt-4o-mini",
    "generate": "anthropic/claude-sonnet-5",
}

# country name/code -> (SerpApi/Apify gl code, human location). Add markets here.
_COUNTRY_GEO = {
    "UK": ("gb", "United Kingdom"), "GB": ("gb", "United Kingdom"),
    "GREAT BRITAIN": ("gb", "United Kingdom"), "UNITED KINGDOM": ("gb", "United Kingdom"),
    "US": ("us", "United States"), "USA": ("us", "United States"),
    "UNITED STATES": ("us", "United States"),
}


def country_geo(country: str | None = None, default: str = "UK") -> tuple[str, str]:
    """Return (gl_code, location_name) for search geo-targeting."""
    key = (country or default or "UK").strip().upper()
    return _COUNTRY_GEO.get(key, ("gb", "United Kingdom"))
