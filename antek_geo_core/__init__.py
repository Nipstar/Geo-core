"""antek-geo-core — shared AI-visibility engine for geo-slab & geo-prospecting.

Single source of truth so the two products can never drift on models, brand
detection, competitor filtering, prompts or scoring again. Canonical versions =
geo-prospecting's (the newer superset).

Modules:
    settings    — env-driven config (no repo coupling)
    models      — CHECK_MODELS (canonical 5 engines), AI_OVERVIEW_ENGINE, country_geo
    providers   — query_openrouter_full(prompt, model, api_key=None); auto-falls
                  back to direct OpenAI (OPENAI_API_KEY) for openai/* models if
                  OpenRouter's upstream provider errors
    brand       — normalize_brand_name, detect_brand_mention, extract_competitors,
                  is_brand_query, is_generic_brand_name, derive_fuller_name
    competitors — competitor gate: valid_competitors, is_self_mention, clean_company_name…
    prompts     — normalise_term, build_prompts(industry, town, county, country, limit)
    aio         — serpapi_ai_overview (SerpApi-first Google AI Overview probe)
    scoring     — composite_score(grid, engines, queries)
"""
from __future__ import annotations

from . import aio, brand, competitors, models, prompts, providers, scoring, settings
from .aio import serpapi_ai_overview
from .brand import (
    derive_fuller_name,
    detect_brand_mention,
    extract_competitors,
    is_brand_query,
    is_generic_brand_name,
    normalize_brand_name,
)
from .competitors import (
    clean_company_name,
    first_valid_competitor,
    is_self_mention,
    is_valid_competitor,
    noun_phrase,
    valid_competitors,
)
from .models import (
    AI_OVERVIEW_ENGINE,
    CHECK_ENGINES,
    CHECK_MODELS,
    country_geo,
)
from .prompts import build_prompts, normalise_term
from .providers import query_openrouter_full
from .scoring import composite_score

__version__ = "0.3.0"

__all__ = [
    "aio", "brand", "competitors", "models", "prompts", "providers", "scoring", "settings",
    # brand
    "normalize_brand_name", "detect_brand_mention", "extract_competitors",
    "is_brand_query", "is_generic_brand_name", "derive_fuller_name",
    # competitors
    "noun_phrase", "is_valid_competitor", "is_self_mention",
    "first_valid_competitor", "valid_competitors", "clean_company_name",
    # models / providers / prompts / aio / scoring
    "CHECK_MODELS", "CHECK_ENGINES", "AI_OVERVIEW_ENGINE", "country_geo",
    "query_openrouter_full", "build_prompts", "normalise_term",
    "serpapi_ai_overview", "composite_score",
    "__version__",
]
