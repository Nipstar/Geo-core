# antek-geo-core

Shared AI-visibility engine for Antek's GEO products — **one source of truth** so
the free tease (`geo-prospecting`) and the paid audit (`geo-slab`) never drift on
models, brand detection, competitor filtering, prompts or scoring.

```python
from antek_geo_core import (
    CHECK_MODELS, query_openrouter_full,          # providers
    detect_brand_mention, extract_competitors,    # brand
    valid_competitors, clean_company_name,        # competitor gate
    build_prompts, normalise_term,                # prompts
    serpapi_ai_overview,                          # Google AI Overview probe
    composite_score, country_geo,                 # scoring / geo
)
```

## Install (both products consume it)
```bash
pip install "git+https://github.com/Nipstar/Geo-core@v0.1.0"
```
Pin the tag — bump it to roll changes so upgrades stay deliberate.

## Env
`OPENROUTER_API_KEY`, `SERPAPI_KEY`, optional `GEO_WEB_SEARCH` (default on),
`GEO_WEB_SEARCH_MAX` (5).

## The canonical 5 engines
ChatGPT · Claude · Gemini · Perplexity (via OpenRouter) + Google AI Overview
(SerpApi). geo-slab's extra engines are additive and live in geo-slab.

## Why
`geo-slab/scripts/lib/ai_query_core.py` and
`geo-prospecting/src/visibility/*` were the same code forked and drifting
(swapped arg order, one had better competitor filtering). This is the
consolidation. Canonical = geo-prospecting's superset. See `GEO_CORE_SPIKE.md`
for the full migration plan + the zero-discrepancy rules.

Tests: `pytest tests/` (golden behaviour lock).
