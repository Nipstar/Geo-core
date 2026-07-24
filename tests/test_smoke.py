"""Golden smoke tests — lock shared-core behaviour so neither product drifts."""
from antek_geo_core import (
    CHECK_MODELS,
    build_prompts,
    clean_company_name,
    composite_score,
    country_geo,
    detect_brand_mention,
    extract_competitors,
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
    # (1/2)*70 + (1/4)*30 = 35 + 7.5 = 42.5
    assert s["composite"] == 42.5
