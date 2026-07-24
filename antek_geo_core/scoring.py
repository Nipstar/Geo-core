"""Composite 0-100 visibility score — canonical formula (geo-prospecting).

    composite = (platforms_mentioned / platforms_tested) * 70
              + (prompts_mentioned  / prompts_total)     * 30

Platform coverage weighted 70 (breadth across engines), prompt coverage 30
(depth across buyer questions). `grid[engine][query]` is truthy when the brand
was mentioned, falsy when tested-but-absent, None when not tested.
"""
from __future__ import annotations


def composite_score(grid: dict, engines: list, queries: list) -> dict:
    """Return {composite, platforms_tested, platforms_mentioned,
    prompts_total, prompts_mentioned}."""
    platforms_tested = sum(
        1 for e in engines if any(grid[e][q] is not None for q in queries))
    platforms_mentioned = sum(
        1 for e in engines if any(grid[e][q] for q in queries))
    prompts_total = sum(
        1 for e in engines for q in queries if grid[e][q] is not None)
    prompts_mentioned = sum(
        1 for e in engines for q in queries if grid[e][q])

    denom_p = platforms_tested or 1
    denom_q = prompts_total or 1
    composite = round((platforms_mentioned / denom_p) * 70
                      + (prompts_mentioned / denom_q) * 30, 1)
    return {
        "composite": composite,
        "platforms_tested": platforms_tested,
        "platforms_mentioned": platforms_mentioned,
        "prompts_total": prompts_total,
        "prompts_mentioned": prompts_mentioned,
    }
