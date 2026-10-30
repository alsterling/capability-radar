"""Scoring, verdicts and top-N.

Evidence outranks popularity by construction: popularity adds at most POPULARITY_CAP, less than one
step of evidence quality, and never changes a verdict.
"""

import math

from .core import UNKNOWN, RECOMMENDATIONS, category_by_id, name_key, parse_date, url_domain
from .profile import job_keywords, stack_keys

EVIDENCE_POINTS = {"STRONG": 4.0, "MODERATE": 3.0, "WEAK": 1.5, "ANECDOTAL": 0.5, UNKNOWN: 0.0}
TIER_POINTS = {"TIER1_OFFICIAL": 2.0, "TIER2_ECOSYSTEM": 1.25, "TIER3_PRACTICAL": 0.5, UNKNOWN: 0.0}
STATUS_POINTS = {"ACTIVE": 1.5, "MAINTAINED": 1.5, "PREVIEW": 0.75, UNKNOWN: 0.25, "STALE": -1.0,
                 "ARCHIVED": -3.0, "DEPRECATED": -3.0}
IMPROVEMENT_POINTS = {"YES": 2.0, UNKNOWN: 0.5, "NO": 0.0}
OVERLAP_POINTS = {"IN_STACK": -1.0, "OVERLAP": -1.0, "NONE": 0.0, UNKNOWN: 0.0}
NATIVE_POINTS = {"YES": -1.5, "PARTIAL": -0.5, "NO": 0.0, UNKNOWN: 0.0}
POPULARITY_CAP = 0.75
VERDICT_ORDER = {"USE": 3, "TEST": 2, "WATCH": 1, "IGNORE": 0}
POPULARITY_KEYS = ("stars", "github_stars", "downloads", "weekly_downloads", "monthly_downloads", "installs", "users")


def popularity_number(pop):
    nums = []
    for k in POPULARITY_KEYS:
        v = (pop or {}).get(k)
        try:
            nums.append(float(str(v).replace(",", "")))
        except (TypeError, ValueError):
            pass
    return max(nums) if nums else None


def stack_overlap(c, prof):
    keys = stack_keys(prof)
    own = {name_key(c["name"])} | {name_key(a) for a in c.get("aliases", [])}
    hits = sorted(keys[k]["name"] for k in own if k in keys)
    if hits:
        return {"level": "IN_STACK", "with": hits}
    named = list(c.get("overlaps_with", []))
    if c.get("current_tool") and c["current_tool"]["relation"] != "COMPLEMENTS":
        named.append(c["current_tool"]["name"])
    hits = sorted({keys[name_key(n)]["name"] for n in named if name_key(n) in keys})
    if hits:
        return {"level": "OVERLAP", "with": hits}
    if named or c.get("current_tool") or c.get("native_overlap") == "NO":
        return {"level": "NONE", "with": []}
    return {"level": UNKNOWN, "with": []}


def score(c, prof, categories, as_of):
    parts = {
        "evidence": EVIDENCE_POINTS[c["evidence_quality"]],
        "source_tier": TIER_POINTS[c["source_tier"]],
        "source_diversity": 0.25 * min(len({url_domain(s["url"]) for s in c["sources"]}), 3),
        "maintenance": STATUS_POINTS[c["status"]],
        "improvement": IMPROVEMENT_POINTS[c["improvement_opportunity"]],
        "native_overlap": NATIVE_POINTS[c["native_overlap"]],
    }
    kw = job_keywords(prof)
    text = " ".join([c["name"], c["job"], c["description"]]).lower()
    parts["job_fit"] = 0.5 * min(sum(1 for w in kw if w in text), 3)
    ov = stack_overlap(c, prof)
    parts["stack_overlap"] = OVERLAP_POINTS[ov["level"]]
    n = popularity_number(c.get("popularity"))
    parts["popularity"] = round(min(POPULARITY_CAP, POPULARITY_CAP * math.log10(n + 1) / 6), 3) if n else 0.0
    lv = parse_date(c["last_verified"])
    fresh = category_by_id(categories, c["category"]).get("freshness_days", 30)
    parts["staleness"] = -0.5 if (lv is None or (as_of - lv).days > fresh) else 0.0
    return round(sum(parts.values()), 3), parts, ov


def ceiling(c):
    """Highest verdict the evidence allows, with the reason for the cap."""
    if c["status"] in ("ARCHIVED", "DEPRECATED"):
        return "IGNORE", f"status {c['status']}"
    if not c["sources"]:
        return "WATCH", "no source captured"
    if c["evidence_quality"] in ("WEAK", "ANECDOTAL", UNKNOWN):
        return "TEST", f"evidence {c['evidence_quality']}"
    if c["benchmark_needed"] == "YES":
        return "TEST", "benchmark needed before USE"
    return "USE", None


def derived_verdict(c, ov):
    if c["status"] in ("ARCHIVED", "DEPRECATED"):
        return "IGNORE", f"{c['status'].lower()}"
    if c["improvement_opportunity"] == "NO" and (c["native_overlap"] == "YES" or ov["level"] in ("IN_STACK", "OVERLAP")):
        return "IGNORE", "no improvement over what is already available"
    if c["improvement_opportunity"] == "NO" and c["evidence_quality"] in ("WEAK", "ANECDOTAL", UNKNOWN):
        return "IGNORE", "no improvement and weak evidence"
    if (c["improvement_opportunity"] == "YES" and c["evidence_quality"] == "STRONG" and c["benchmark_needed"] == "NO"
            and c["source_tier"] == "TIER1_OFFICIAL" and c["status"] in ("ACTIVE", "MAINTAINED")):
        return "USE", "strong official evidence of a real improvement, no benchmark needed"
    if c["improvement_opportunity"] == "YES" and c["evidence_quality"] != UNKNOWN:
        return "TEST", "plausible improvement; prove it on your own job first"
    if c["improvement_opportunity"] == UNKNOWN and c["evidence_quality"] in ("STRONG", "MODERATE"):
        return "TEST", "credible capability; improvement for this profile unproven"
    return "WATCH", "not enough evidence of an improvement yet"


def evaluate(c, prof, categories, as_of):
    """Live view of a ledger entry: score, verdict (Skill's recommendation capped by evidence), overlap."""
    s, parts, ov = score(c, prof, categories, as_of)
    cap, cap_reason = ceiling(c)
    if c.get("recommendation") in RECOMMENDATIONS:
        verdict, source = c["recommendation"], "SKILL"
        reason = c["reason"] if c["reason"] != UNKNOWN else "recommended by scan"
    else:
        (verdict, reason), source = derived_verdict(c, ov), "DERIVED"
    guard = None
    if VERDICT_ORDER[verdict] > VERDICT_ORDER[cap]:
        guard = f"{verdict} capped to {cap}: {cap_reason}"
        verdict = cap
    return {**c, "score": s, "score_parts": parts, "stack_overlap": ov, "verdict": verdict,
            "verdict_source": source, "verdict_reason": reason, "guard": guard}


def rank(entries, prof, categories, as_of, category=None, top=None, include_ignored=False):
    views = [evaluate(e, prof, categories, as_of) for e in entries
             if category is None or e["category"] == category]
    if not include_ignored:
        views = [v for v in views if v["verdict"] != "IGNORE"]
    views.sort(key=lambda v: (-VERDICT_ORDER[v["verdict"]], -v["score"], v["name"].lower()))
    return views[:top] if top else views


def top_opportunities(entries, prof, categories, as_of, top=10):
    """Things worth changing: improvement YES, verdict USE/TEST, not already in the stack."""
    views = [v for v in rank(entries, prof, categories, as_of)
             if v["improvement_opportunity"] == "YES" and v["verdict"] in ("USE", "TEST")
             and v["stack_overlap"]["level"] != "IN_STACK"]
    views.sort(key=lambda v: (-v["score"], v["name"].lower()))
    return views[:top]
