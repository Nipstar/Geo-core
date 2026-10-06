"""Canonical 0-100 visibility score.

The headline is the recommendation rate: the share of answered engine×query
cells which mention the brand. ``grid[engine][query]`` is truthy when
mentioned, falsy when answered but absent, and ``None`` when untested.
"""
from __future__ import annotations

# Default to pure recommendation rate. Change these two constants to opt into
# the proportional (never binary) per-engine breadth blend.
DEPTH_WEIGHT = 1.0
BREADTH_WEIGHT = 0.0


def composite_score(grid: dict, engines: list, queries: list) -> dict:
    """Return the headline and its coverage/count reporting fields.

    Raises when no engine returned an answer: API failure must never be
    represented as genuine zero visibility.
    """
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

    if platforms_tested == 0:
        raise ValueError("No engine returned an answer; visibility cannot be scored")

    cell_rate = prompts_mentioned / prompts_total
    per_engine_rates = [
        sum(1 for q in queries if grid[e][q])
        / sum(1 for q in queries if grid[e][q] is not None)
        for e in engines
        if any(grid[e][q] is not None for q in queries)
    ]
    proportional_breadth = sum(per_engine_rates) / len(per_engine_rates)
    composite = round(100 * (
        DEPTH_WEIGHT * cell_rate + BREADTH_WEIGHT * proportional_breadth
    ), 1)
    return {
        "composite": composite,
        "platforms_tested": platforms_tested,
        "platforms_mentioned": platforms_mentioned,
        "prompts_total": prompts_total,
        "prompts_mentioned": prompts_mentioned,
    }
