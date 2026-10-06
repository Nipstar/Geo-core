"""Canonical 0-100 visibility score.

The headline is the recommendation rate: the share of answered engine×query
cells which mention the brand. ``grid[engine][query]`` is truthy when
mentioned, falsy when answered but absent, and ``None`` when untested.

Two entry points, ONE formula:
  * ``composite_score(grid, engines, queries)`` — for callers holding a grid
    (e.g. geo-slab). Builds the counts, then delegates.
  * ``composite_from_counts(...)`` — for callers that already hold the aggregate
    counts (e.g. geo-prospecting score.py / report.py). No grid required.
Both return the same dict shape and obey the same weights below.
"""
from __future__ import annotations

# Default to pure recommendation rate. Change these two constants to opt into
# the proportional (never binary) per-engine breadth blend.
DEPTH_WEIGHT = 1.0
BREADTH_WEIGHT = 0.0


def composite_from_counts(
    platforms_tested: int,
    platforms_mentioned: int,
    prompts_total: int,
    prompts_mentioned: int,
    per_engine_rates: list | None = None,
) -> dict:
    """Score from already-aggregated counts. Single source of the formula.

    Raises when no engine returned an answer: API failure must never be
    represented as genuine zero visibility.

    ``per_engine_rates`` (list of mentioned/answered per tested engine) is only
    needed when ``BREADTH_WEIGHT > 0`` to compute the proportional breadth term.
    With the default pure recommendation-rate weighting it is ignored.
    """
    if platforms_tested == 0:
        raise ValueError("No engine returned an answer; visibility cannot be scored")

    cell_rate = (prompts_mentioned / prompts_total) if prompts_total else 0.0

    if BREADTH_WEIGHT:
        if per_engine_rates:
            breadth = sum(per_engine_rates) / len(per_engine_rates)
        else:
            # No grid available: fall back to binary coverage. Proportional
            # breadth needs the grid; callers wanting it must use composite_score.
            breadth = platforms_mentioned / platforms_tested
    else:
        breadth = 0.0

    composite = round(100 * (DEPTH_WEIGHT * cell_rate + BREADTH_WEIGHT * breadth), 1)
    return {
        "composite": composite,
        "platforms_tested": platforms_tested,
        "platforms_mentioned": platforms_mentioned,
        "prompts_total": prompts_total,
        "prompts_mentioned": prompts_mentioned,
    }


def composite_score(grid: dict, engines: list, queries: list) -> dict:
    """Return the headline and its coverage/count reporting fields from a grid."""
    platforms_tested = sum(
        1 for e in engines if any(grid[e][q] is not None for q in queries)
    )
    platforms_mentioned = sum(
        1 for e in engines if any(grid[e][q] for q in queries)
    )
    prompts_total = sum(
        1 for e in engines for q in queries if grid[e][q] is not None
    )
    prompts_mentioned = sum(
        1 for e in engines for q in queries if grid[e][q]
    )
    per_engine_rates = [
        sum(1 for q in queries if grid[e][q])
        / sum(1 for q in queries if grid[e][q] is not None)
        for e in engines
        if any(grid[e][q] is not None for q in queries)
    ]
    return composite_from_counts(
        platforms_tested,
        platforms_mentioned,
        prompts_total,
        prompts_mentioned,
        per_engine_rates=per_engine_rates,
    )
