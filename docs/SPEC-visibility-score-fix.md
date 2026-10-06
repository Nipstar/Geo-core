# SPEC — Fix misleading visibility composite (geo-prospecting + geo-slab)

Status: DRAFT (awaiting final weighting sign-off from Andy)
Author: main (Antek orchestrator)
Scope: Geo-core + geo-prospecting + geo-slab (shared 70/30 rubric)

## 1. Problem

Current composite (all three impls below) is **breadth-weighted and overstates
real AI-search visibility**:

```
composite = (platforms_mentioned / platforms_tested) * 70
          + (prompts_mentioned  / prompts_total)     * 30
```

`platforms_mentioned` is **binary per engine** — a brand mentioned on even ONE
of N prompts counts that whole engine as "mentioned" and earns full breadth
credit. So the 70-point term is near-saturated for any brand that shows up at
all.

Evidence — RadioCloud check 887:
- Real hit-rate: **5 of 40** engine×query cells = **12.5%**.
- Scored **59.8/100** because 4/5 engines had ≥1 mention → 4/5×70 = 56, +5/40×30 = 3.8.
- A prospect reads "60" as healthy visibility; reality is barely recommended.

## 2. Current locations (3 copies — must converge)

| File | Lines | State |
|---|---|---|
| `Geo-core/antek_geo_core/scoring.py` `composite_score()` | ~13-34 | canonical shared fn, **not adopted** by either repo |
| `geo-prospecting/src/visibility/score.py` | 94-98 | inline, independent |
| `geo-slab/scripts/visibility_check.py` | 279-281 | inline, independent |

## 3. Fix — single source of truth

1. Rewrite `antek_geo_core.scoring.composite_score()` with the new model (§4).
2. `geo-prospecting/src/visibility/score.py` and
   `geo-slab/scripts/visibility_check.py` DELETE their inline math and CALL
   `composite_score(...)`. No formula may live outside Geo-core after this.
3. Bump Geo-core, re-pin both repos' vendored/.venv copy (geo-slab vendors
   `antek_geo_core` in `.venv`; ensure the pin updates, not just the source).

## 4. New model (DEFAULT — recommendation-rate)

Headline composite = **how often the brand is actually recommended**, i.e. the
share of answered engine×query cells where the brand appears. Breadth stays, but
only as a **separate reported badge** — it never inflates the headline.

```python
# denominators guard div-by-zero; raise upstream if platforms_tested == 0
cell_rate = prompts_mentioned / prompts_total            # 0..1, the real signal
composite = round(100 * cell_rate, 1)                    # RadioCloud -> 12.5

# reported ALONGSIDE composite, not folded into it:
engines_covered   = platforms_mentioned                  # e.g. 4
engines_tested    = platforms_tested                     # e.g. 5
per_engine_rate_e = mentioned_e / answered_e             # already computed
```

### Configurable blend (if a breadth bonus is wanted later)
Expose module constants so the weighting is a one-line change, never a rewrite:

```python
BREADTH_WEIGHT = 0.0   # default: pure recommendation-rate
DEPTH_WEIGHT   = 1.0
# breadth uses MEAN per-engine hit-rate (proportional), NOT binary coverage,
# so a single mention can never buy full engine credit:
breadth = mean(mentioned_e / answered_e for e in tested_engines)
composite = round(100 * (DEPTH_WEIGHT * cell_rate + BREADTH_WEIGHT * breadth), 1)
```

Reference points for RadioCloud (5/40 cells, 4/5 engines):
- DEPTH=1.0 / BREADTH=0.0  → **12.5** (recommended default)
- 70/30 depth-weighted (binary breadth) → 33
- 50/50 proportional blend → 12.5 (diverges only when engines answer uneven #queries)

## 5. Report / headline changes (both repos)

- Client report headline must state the **cell-rate in plain English**
  ("recommended in 5 of 40 answers across 5 engines"), not just the number.
- Keep the "appears on X/Y engines" coverage badge as a DISTINCT line.
- Dev/operator report: already shows the per-query grid — add a per-engine
  hit-rate column (`mentioned_e/answered_e`) so the depth is explicit.
- Do NOT let Google-specific caveats touch weights (standing rule: advice
  framing only; tool scores all engines equally).

## 6. Invariants to preserve (regression guard)

- `platforms_tested == 0` still RAISES (dead API key ≠ genuine 0/100).
- Brand-query exclusion stays code-enforced via `is_brand_query()` — brand-name
  prompts must not be scored as organic visibility.
- Known `detect_brand_mention` looseness for two-word category-phrase brands
  (e.g. "Agency AI") is a SEPARATE flagged bug; this spec does not fix it but
  must not make it worse.

## 7. Tests (TDD — write first, both repos / core)

1. 5/40 cells, 4/5 engines → composite 12.5 (not ~60).
2. All 40 cells hit → 100.0; 0 cells hit → 0.0.
3. Uneven answers (engine A answers 2 queries both hit, engine B answers 8 none
   hit) → proportional blend ≠ binary result; assert expected.
4. platforms_tested == 0 → raises.
5. Geo-core fn and both repo call-sites return identical dict for same grid
   (parity test — proves inline math is gone).

## 8. Rollout

- Scores drop materially for existing reports. Decide: re-score live set or only
  new checks. (Recommend: re-build live reports from stored probe_cache — no new
  spend — so old deployed numbers don't contradict new ones.)
- Mirror the Geo-core bump to geo-slab's vendored copy in the SAME change.
