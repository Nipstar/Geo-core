"""Brand detection + first-pass competitor extraction (regex, no 2nd AI call).

CANONICAL = geo-prospecting's version (a superset of geo-slab's: it adds the
'how-to-choose advice' noise filters so the "a competitor was recommended
instead" hook doesn't fire on junk like 'Location' / 'Fees' / 'Reviews').

For letter/report-grade competitor lists, pass the output through
`antek_geo_core.competitors.valid_competitors()` (the competitor_gate rules).
"""
from __future__ import annotations

import re
from urllib.parse import urlparse


def normalize_brand_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower().strip())


# --- Brand-name query handling ----------------------------------------------
# Both consumer products ran into the same class of bug independently before
# this was made canonical here:
#   - geo-prospecting (score.py, 2026-08-06/07): a self-referential scored
#     query ("What is Acme Ltd?") trivially passes on every AI engine — the
#     question already contains the answer — so mixing one into a scored
#     query set inflated a composite from a true 0/100 to a misleading 76/100.
#   - geo-slab (brand_scanner.py, 2026-08-08): a single short generic-word
#     brand name (e.g. "Regen") returns near-100% noise from live search,
#     reporting "zero presence anywhere" when the fuller domain-derived name
#     ("Regen Digital") finds the business's real profiles immediately.
# Both are the same root problem — a bare/self-referential brand string
# doesn't discriminate the way a real discovery query does — so both fixes
# live together here instead of drifting as two separate implementations.

_SUFFIX_RE = re.compile(r"\b(ltd|limited|llp|plc|inc|co)\b", re.I)
_PUNCT_RE = re.compile(r"[^a-z0-9 ]")


def _core_brand_tokens(name: str) -> str:
    core = _SUFFIX_RE.sub("", (name or "").lower())
    core = _PUNCT_RE.sub(" ", core)
    return re.sub(r"\s+", " ", core).strip()


def is_brand_query(query: str, company_name: str) -> bool:
    """True if the query text itself names the company (e.g. "What is Acme
    Ltd?", "Acme reviews"). Such queries trivially pass on every AI engine
    that has ever indexed the company's own site — the question already
    contains the answer — so callers should exclude these from any scored
    query set. Still worth probing/displaying for brand-recognition info,
    just never counted toward a composite or per-engine score.

    Usage (geo-prospecting's score_company()): split queries into scored vs
    brand before running probes; sum scoring tallies only over the scored
    set. See antek_geo_core README / geo-prospecting's
    ai-visibility-check-manual skill for the full pattern."""
    core = _core_brand_tokens(company_name)
    if not core:
        return False
    return core in (query or "").lower()


def is_generic_brand_name(brand: str) -> bool:
    """True for a single short common-word-shaped brand name (e.g. "Regen",
    "Nova", "Apex") — the case where a bare live-search query returns
    near-100% noise and produces a false "no presence anywhere" finding.
    Callers should also try derive_fuller_name() and compare/merge results
    rather than trusting the bare-name search alone."""
    return " " not in brand.strip() and len(brand.strip()) <= 8


def derive_fuller_name(brand: str, domain: str | None) -> str | None:
    """Best-effort: if `brand` is a short single word and `domain`'s first
    label looks like brand+descriptor concatenated (e.g. brand="Regen",
    domain="regendigital.co" -> label "regendigital"), split off the
    remainder and return a fuller candidate name ("Regen Digital"). Not a
    real word-segmenter — returns None rather than guessing when it can't be
    confident (remainder isn't alphabetic, or domain doesn't start with the
    brand at all).

    Callers doing a live brand-mention scan should, when is_generic_brand_name
    is true and this returns a candidate, run checks for BOTH names and merge
    per-signal — keep whichever name actually found real presence (see
    geo-slab's brand_scanner.py for the reference merge implementation).
    This must not be left as a manual "consider also trying..." step: a
    stderr nudge that relies on an operator noticing and re-running is
    exactly the pattern that produced the original bug (regendigital.co,
    2026-08-08 — bare "Regen" was reported as zero presence anywhere when
    "Regen Digital" found the real LinkedIn page at position 1)."""
    if not domain:
        return None
    label = re.sub(r"^www\.", "", domain.strip().lower()).split(".")[0]
    brand_l = re.sub(r"[^a-z0-9]", "", brand.lower())
    if not brand_l or not label.startswith(brand_l):
        return None
    remainder = label[len(brand_l):]
    if not remainder.isalpha():
        return None
    return f"{brand.strip()} {remainder.capitalize()}"


def detect_brand_mention(text: str, brand_name: str, url: str = "") -> dict:
    """Regex brand detection. Returns mentioned/count/positions/sentiment."""
    if not text or not brand_name:
        return {"mentioned": False, "count": 0, "positions": [], "sentiment": "neutral"}

    brand_normalized = normalize_brand_name(brand_name)
    domain = ""
    if url:
        domain = urlparse(url if "//" in url else f"//{url}").netloc.replace("www.", "")

    patterns = [re.compile(r"\b" + re.escape(brand_name) + r"\b", re.IGNORECASE)]
    if domain:
        patterns.append(re.compile(re.escape(domain), re.IGNORECASE))
    if len(brand_name.split()) > 1:
        patterns.append(re.compile(r"\b" + re.escape(brand_normalized) + r"\b", re.IGNORECASE))

    count = 0
    positions: list[str] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            count += 1
            start = max(0, match.start() - 60)
            end = min(len(text), match.end() + 60)
            positions.append(text[start:end].strip())

    sentiment = "neutral"
    if count > 0:
        text_lower = text.lower()
        positive = ["recommend", "best", "great", "excellent", "top", "leading",
                    "trusted", "reliable", "popular", "preferred", "outstanding"]
        negative = ["avoid", "poor", "worst", "bad", "terrible", "unreliable",
                    "scam", "complaint", "issue", "problem"]
        pos = sum(1 for w in positive if w in text_lower)
        neg = sum(1 for w in negative if w in text_lower)
        if pos > neg:
            sentiment = "positive"
        elif neg > pos:
            sentiment = "negative"

    return {"mentioned": count > 0, "count": count, "positions": positions[:5], "sentiment": sentiment}


def extract_competitors(text: str, brand_name: str) -> list[str]:
    """Pull competitor-like names from list items and bold text (first pass)."""
    competitors: set[str] = set()
    brand_norm = normalize_brand_name(brand_name)

    list_pattern = re.compile(
        r"(?:^|\n)\s*(?:\d+[\.\)]\s*\**|[-*]\s*\**)"
        r"([A-Z][A-Za-z0-9\s&'-]{2,40}?)(?:\**\s*[-–—:]|\**\s*\n|\**$)",
        re.MULTILINE,
    )
    bold_pattern = re.compile(r"\*\*([A-Z][A-Za-z0-9\s&'-]{2,40}?)\*\*")

    for pat in (list_pattern, bold_pattern):
        for match in pat.finditer(text):
            name = match.group(1).strip().rstrip("*").strip()
            if normalize_brand_name(name) != brand_norm and len(name) > 2:
                competitors.add(name)

    noise = {
        "the best", "the top", "the most", "in conclusion", "for example",
        "in summary", "key features", "main benefits", "important factors",
        "here are", "some options", "final thoughts", "pros and cons",
        "word of mouth", "online search", "local directories", "local directory",
        "online reviews", "google reviews", "google search", "google maps",
        "social media", "personal recommendations", "recommendations",
        "check reviews", "ask friends", "search online", "review sites",
        "review platforms", "local search", "trade associations", "gas safe register",
        "location", "fees", "pricing", "cost", "costs", "experience",
        "qualifications", "professional qualifications", "credentials",
        "accreditation", "accreditations", "services offered", "services",
        "professional associations", "professional bodies", "professional body",
        "value for money", "specialization", "specialisation", "reputation",
        "availability", "communication", "references", "reviews and ratings",
        "local business directories", "local recommendations",
        "ask for recommendations", "range of services", "client reviews",
        "industry experience", "areas of expertise", "expertise", "self",
    }
    directories = {
        "trustpilot", "yell", "yelp", "checkatrade", "bark", "bark.com",
        "google", "google business", "google my business", "bing", "facebook",
        "linkedin", "thomson local", "yellow pages", "yellowpages", "192.com",
        "freeindex", "cylex", "scoot", "houzz", "which", "which?", "tripadvisor",
        "rightmove", "zoopla", "onthemarket",
        "chatgpt", "openai", "perplexity", "gemini", "claude", "reddit", "quora",
    }
    postcode_frag = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?(\s*\d[A-Z]{2})?$", re.I)
    signals = ("ltd", "llp", "& co", "accountant", "accountancy", "associates",
               "partners", "group", "chartered", "bookkeep", "advisor", "advisory",
               "solutions", "consultancy", "consulting", "financial", "plc", "limited",
               "estates", "lettings", "homes", "property", "solicitors")
    generic = {
        "experience", "qualifications", "qualification", "directories", "directory",
        "consultation", "consultations", "referrals", "referral", "reviews", "review",
        "testimonials", "testimonial", "fees", "fee", "pricing", "price", "cost", "costs",
        "networks", "network", "communication", "style", "expertise", "specialisation",
        "specialization", "availability", "reputation", "consideration", "considerations",
        "formation", "services", "service", "contact", "details", "recommendations",
        "recommendation", "friends", "family", "structure", "initial",
        "online", "local", "other", "businesses", "business", "clear", "consider",
        "what", "ask", "and", "for", "with", "your", "type", "value", "money",
    }

    def is_firm(name: str) -> bool:
        s = name.strip()
        low = s.lower()
        if low in noise or low in directories or len(s) <= 3 or postcode_frag.match(s):
            return False
        if any(sig in low for sig in signals):
            return True
        toks = [t for t in s.split() if t != "&"]
        if len(toks) < 2 or len(toks) > 4:
            return False
        if any(t.lower() in generic for t in toks):
            return False
        return all(t[:1].isupper() for t in toks)

    return sorted(c for c in competitors if is_firm(c))
