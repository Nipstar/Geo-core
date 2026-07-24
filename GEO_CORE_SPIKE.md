# antek-geo-core — extraction spike

**Goal:** one shared library for the AI-visibility engine so `geo-slab` and
`geo-prospecting` can never drift again. This repo is the spike skeleton; it
imports and passes golden checks. Phases below finish the migration.

## Why (the drift, measured)
`geo-slab/scripts/lib/ai_query_core.py` and
`geo-prospecting/src/visibility/ai_query.py` are the **same code, forked**:

| Function | Status |
|---|---|
| `CHECK_MODELS` | **identical** (gpt-5.2-chat / sonnet-5 / gemini-2.5-flash / sonar) |
| `detect_brand_mention` | ~identical (only type hints differ) |
| `normalize_brand_name` | identical |
| `extract_competitors` | **geo-prospecting is a superset** (adds the "how-to-choose junk" filters) |
| `query_openrouter_full` | **arg order swapped** — slab `(prompt, api_key, model)` vs pros `(prompt, model, api_key)` → silent-drift landmine |
| competitor gating | **geo-prospecting only** (`competitor_gate.py`) — slab has none |

**Canonical = geo-prospecting** everywhere they diverge (newer + superset).

## Package layout (this repo)
```
antek_geo_core/
  settings.py     ✅ env-driven config (no repo coupling)
  models.py       ✅ CHECK_MODELS, AI_OVERVIEW_ENGINE, country_geo
  providers.py    ✅ query_openrouter_full(prompt, model, api_key=None)  ← canonical sig
  brand.py        ✅ normalize_brand_name, detect_brand_mention, extract_competitors
  competitors.py  ⏳ port competitor_gate.py
  prompts.py      ⏳ port normalise_term + build_prompts (field-based primitive)
  aio.py          ⏳ port SerpApi-first AI Overview probe
  scoring.py      ⏳ port composite formula
tests/test_smoke.py  ✅ golden behaviour lock
```
✅ = built + passing.  ⏳ = documented stub (raises NotImplementedError with source pointer).

## Product boundary (locked)
Two separate products; one shared engine.

- **geo-prospecting = THE HOOK/TEASE.** Free AI Visibility check → shows *what's*
  wrong → claim page → book a call. Job = get the meeting. Stays lean: NO paid
  audit / fix logic here. Keeps: `probe_cache`, letters (US/UK, gender salutations),
  claim-site funnel + hooks, Places/Apollo/Sunbiz/LinkedIn ingest, n8n capture.
- **geo-slab = THE SERVICE.** Full audit (citability/technical/schema) **+ the
  fix** — the paid deliverable, run after they book. Keeps: skills + agents,
  webapp, Flask `check_api`, citability scorer, pitchability, neo-brutalist reports.
- **antek-geo-core = THE SHARED ENGINE.** The visibility-check only. **Reason it
  must be shared:** the free score the prospect sees has to equal the visibility
  section of slab's paid audit — same engine, same numbers, or trust breaks.

### Lead handoff (prospecting → slab)
Prospecting captures the email inbound (claim form → n8n → Brevo list). That lead
is the input to slab's full audit. Design a thin bridge (Brevo tag / webhook /
shared prospect ref) so a booked lead flows from the tease into the service. Not
a code merge — a pipeline handoff.

### ZERO-DISCREPANCY GUARANTEE (hard requirement)
The free score a prospect sees must never contradict slab's paid audit. Shared
engine gives *method* parity; it does NOT give *data* parity. Four rules:

1. **Shared engine** — both call `antek-geo-core` (same models/prompts/detection/score).
2. **Persist the free result as source of truth.** The free check stores the full
   finding (score, per-engine mention, competitors, RAW AI answers, run-date)
   keyed to a prospect ref. slab's audit **reuses that stored record** for its
   visibility section — it does NOT silently re-run and re-derive different numbers.
3. **Superset queries.** The paid audit's prompt set must include the free 3 (plus
   its extra depth), so the free finding stays a valid subset.
3b. **Superset engines.** antek-geo-core owns the CANONICAL 5 engines
   (ChatGPT/Claude/Gemini/Perplexity + Google AI Overview) — both products score
   those identically off the stored record. slab's EXTRA engines (6–9) are
   ADDITIVE, presented as "engines only covered in the full audit" — never a
   re-score of the shared 5. Show two framed numbers: tease "across 5 engines",
   audit same-5 (matching) PLUS "across 9 engines" (an explicit superset = a
   selling point, not a contradiction). Extra engines live entirely in slab.
4. **Dated re-runs only.** If the audit re-checks live (fresher data at the call),
   show it as before/after with dates — *"12 Jul: 1/5 → 2 Aug: 3/5"* — framed as
   change, never a silent contradiction.

Implication for the handoff: carry the **stored visibility record** (not just the
email) from prospecting into slab. The visibility check happens ONCE at tease
time; the audit displays it + builds the fix on top.

## Migration plan
**Phase 1 — foundation (this spike):** ✅ package + models/providers/brand + tests.

**Phase 2 — finish the core (~half day):**
port `competitors.py`, `prompts.py`, `aio.py`, `scoring.py` from geo-prospecting;
expand golden tests to lock outputs.

**Phase 3 — wire geo-prospecting (~half day):**
add dep (`pip install git+https://github.com/Nipstar/Geo-core@v0.1.0`);
replace bodies of `ai_query.py` / `competitor_gate.py` / `prompts.py` / scoring
with `from antek_geo_core import …`. Keep `probes.py` cache layer, wrap core AIO.
Run an existing `check mini` on a sample → confirm byte-identical output.

**Phase 4 — wire geo-slab (~half day):**
`ai_query_core.py` becomes a shim re-exporting from `antek_geo_core`; update the
`query_openrouter_*` wrappers to the canonical arg order; run `visibility_check.py`
on a sample → confirm identical output. Delete the duplicated code.

## Risks / decisions
- **Arg-order swap** (`query_openrouter_full`): standardise on pros order; update
  geo-slab's per-model wrappers. One-time, mechanical.
- **Keyword superset**: slab *gains* the junk filters (behaviour change = an
  improvement; lock via golden tests).
- **Prompt input shape** differs (company-row vs raw fields): core exposes the
  raw-field primitive; each repo keeps a 5-line adapter.
- **Multi-provider path**: geo-slab's `live_ai_query.py` can also hit provider
  APIs directly (OpenAI/Anthropic/…). Decide: migrate to OpenRouter-only (simpler)
  or keep direct-provider as a slab-only redundancy. Recommend OpenRouter-only.

## Distribution
Its own **private repo `Nipstar/Geo-core`**, pip-installed by both via a
pinned git tag (`@v0.1.0`). Bump the tag to roll changes — upgrades stay
deliberate, no accidental drift.

## Effort
~1.5–2 dev-days total (phases 2–4). Foundation done.
