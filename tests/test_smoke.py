"""Golden smoke tests — lock shared-core behaviour so neither product drifts."""
from antek_geo_core import (
    CHECK_MODELS,
    build_prompts,
    clean_company_name,
    composite_score,
    country_geo,
    derive_fuller_name,
    detect_brand_mention,
    extract_competitors,
    is_brand_query,
    is_generic_brand_name,
    is_self_mention,
    normalize_brand_name,
    normalise_term,
    valid_competitors,
)


def test_models_frozen():
    assert CHECK_MODELS["ChatGPT"] == "openai/gpt-5.2-chat"
    assert CHECK_MODELS["Perplexity"] == "perplexity/sonar"
    assert set(CHECK_MODELS) == {"ChatGPT", "Claude", "Gemini", "Perplexity"}


def test_geo():
    assert country_geo("US") == ("us", "United States")
    assert country_geo("UK") == ("gb", "United Kingdom")
    assert country_geo(None) == ("gb", "United Kingdom")


def test_detect_mention():
    txt = "The best agent in town is Northstar Realty, highly recommended."
    r = detect_brand_mention(txt, "Northstar Realty")
    assert r["mentioned"] and r["count"] >= 1 and r["sentiment"] == "positive"
    assert detect_brand_mention(txt, "Nobody Ltd")["mentioned"] is False


def test_extract_filters_junk():
    txt = ("1. **Keller Williams Realty** - big\n"
           "2. **Coastal Homes Group** - boutique\n"
           "3. **Location** - area\n4. **Reviews** - check online\n")
    comps = extract_competitors(txt, "My Firm")
    assert "Keller Williams Realty" in comps and "Coastal Homes Group" in comps
    assert "Location" not in comps and "Reviews" not in comps


def test_competitor_gate():
    assert normalize_brand_name("Luxury & Beach Realty, Inc") == "luxurybeachrealtyinc"
    # directory + page-label junk rejected, real firm kept
    got = valid_competitors(["Google Maps", "Services Offered", "Paris Smith LLP"])
    assert got == ["Paris Smith LLP"]
    # self-mention removed
    assert is_self_mention("Clarke & Son Solicitors", "Clarke & Son")
    assert clean_company_name("The Accounting Studio - Accountant Southampton",
                              "Southampton") == "The Accounting Studio"


def test_build_prompts_parity():
    # same fields -> same prompts (query-parity guarantee)
    a = build_prompts("real estate agency", "St. Petersburg", "Florida", limit=3)
    b = build_prompts("real estate agency", "St. Petersburg", "Florida", limit=3)
    assert a == b and len(a) == 3
    assert "St. Petersburg, Florida" in a[0]
    sing, plur, countable = normalise_term("solicitors")
    assert countable and plur == "solicitors"


def test_is_brand_query():
    # self-referential query trivially passes on every engine -- excluded
    # from scored sets so it can't inflate a composite (2026-08-06/07 bug)
    assert is_brand_query("What is Acme Ltd?", "Acme Ltd") is True
    assert is_brand_query("Acme Ltd reviews", "Acme Ltd") is True
    assert is_brand_query("Best marketing agency near me", "Acme Ltd") is False
    assert is_brand_query("", "Acme Ltd") is False


def test_generic_brand_name_handling():
    # single short word -> flagged generic, near-100% search noise otherwise
    # (2026-08-08 bug: bare "Regen" reported zero presence anywhere)
    assert is_generic_brand_name("Regen") is True
    assert is_generic_brand_name("Antek Automation") is False
    assert is_generic_brand_name("Nova") is True
    # domain-derived fuller form: brand+descriptor concatenated in the label
    assert derive_fuller_name("Regen", "regendigital.co") == "Regen Digital"
    assert derive_fuller_name("Regen", "www.regendigital.co") == "Regen Digital"
    # no confident split -> None, never guess
    assert derive_fuller_name("Regen", "unrelated.com") is None
    assert derive_fuller_name("Regen", None) is None


def test_composite_score():
    engines = ["ChatGPT", "Claude", "Gemini"]
    queries = ["q1", "q2"]
    grid = {
        "ChatGPT": {"q1": True, "q2": False},
        "Claude": {"q1": False, "q2": False},
        "Gemini": {"q1": None, "q2": None},   # not tested
    }
    s = composite_score(grid, engines, queries)
    assert s["platforms_tested"] == 2 and s["platforms_mentioned"] == 1
    assert s["prompts_total"] == 4 and s["prompts_mentioned"] == 1
    # Pure recommendation rate (DEPTH_WEIGHT=1.0, BREADTH_WEIGHT=0.0):
    # cell_rate = prompts_mentioned/prompts_total = 1/4 -> 100*0.25 = 25.0.
    # Binary breadth (1/2 engines) is reported, never folded into the headline.
    assert s["composite"] == 25.0
