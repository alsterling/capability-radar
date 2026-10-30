"""Scoring, verdicts, top-N and capability-level opportunities.

Evidence outranks popularity by construction: popularity adds at most POPULARITY_CAP, less than one
step of evidence quality, and never changes a verdict.
"""

import math
from collections import Counter

from .core import UNKNOWN, RECOMMENDATIONS, capability_key, category_by_id, parse_date, url_domain
from .profile import job_terms, stack_key, stack_keys, terms

EVIDENCE_POINTS = {"STRONG": 4.0, "MODERATE": 3.0, "WEAK": 1.5, "ANECDOTAL": 0.5, UNKNOWN: 0.0}
TIER_POINTS = {"TIER1_OFFICIAL": 2.0, "TIER2_ECOSYSTEM": 1.25, "TIER3_PRACTICAL": 0.5, UNKNOWN: 0.0}
STATUS_POINTS = {"ACTIVE": 1.5, "MAINTAINED": 1.5, "PREVIEW": 0.75, UNKNOWN: 0.25, "STALE": -1.0,
                 "ARCHIVED": -3.0, "DEPRECATED": -3.0}
IMPROVEMENT_POINTS = {"YES": 2.0, UNKNOWN: 0.5, "NO": 0.0}
POPULARITY_CAP = 0.75
# KEEP sorts below WATCH so owned items never head a lane; only an ARCHIVED/DEPRECATED cap (IGNORE) lowers it.
VERDICT_ORDER = {"USE": 4, "TEST": 3, "WATCH": 2, "KEEP": 1, "IGNORE": 0}
POPULARITY_KEYS = ("stars", "github_stars", "downloads", "weekly_downloads", "monthly_downloads", "installs", "users")

# Relation to the current stack. Only DUPLICATES is penalized, and only once.
OWNED = "ALREADY_OWNED_SAME_CAPABILITY"
COMPLEMENTS = "COMPLEMENTS_CURRENT_STACK"
DUPLICATES = "DUPLICATES_CURRENT_STACK"
NEW = "NEW_CAPABILITY"
DUPLICATE_POINTS = {"YES": -1.5, "PARTIAL": -0.5}  # by native_overlap degree; any other value -> DUPLICATE_DEFAULT
DUPLICATE_DEFAULT = -1.0

# job_fit: see per_job_fit.
JOB_MIN_HITS = 2       # a job matches only when at least 2 of its terms appear in the candidate
JOB_FULL_FIT = 0.5     # matching half of one job's terms is a full fit
JOB_FIT_POINTS = 1.5   # score points for job_fit 1.0

# Capability opportunity score (0-10): see capability_opportunities.
OPP_WEIGHTS = {"relevance": 3.0, "gap": 2.5, "credibility": 2.0, "evidence": 1.5, "improvement": 1.0, "weak_share": -1.0}
COVERAGE_GAP = {"NONE": 1.0, UNKNOWN: 0.75, "PARTIAL": 0.6, "COVERED": 0.0}
CREDIBILITY = {"USE": 1.0, "TEST": 0.75, "WATCH": 0.25}
ACTIONABLE = ("USE", "TEST", "WATCH")


def popularity_number(pop):
    nums = []
    for k in POPULARITY_KEYS:
        v = (pop or {}).get(k)
        try:
            nums.append(float(str(v).replace(",", "")))
        except (TypeError, ValueError):
            pass
    return max(nums) if nums else None


def stack_relation(c, prof):
    """Where the candidate sits relative to the current stack.

    ALREADY_OWNED_SAME_CAPABILITY  its name/alias is a stack item (every word equal), or the scan marked it owned: YES
    COMPLEMENTS_CURRENT_STACK      current_tool relation COMPLEMENTS (integrates with something owned)
    DUPLICATES_CURRENT_STACK       names a stack item in overlaps_with / a non-complementing current_tool,
                                   or native_overlap YES/PARTIAL (the owned platforms already do it)
    NEW_CAPABILITY                 native_overlap NO, or the tools it names are not owned
    UNKNOWN                        nothing to go on
    """
    keys = stack_keys(prof)
    own = {stack_key(c["name"])} | {stack_key(a) for a in c.get("aliases", [])}
    hits = sorted(keys[k]["name"] for k in own if k in keys)
    ct = c.get("current_tool")
    if hits or c.get("owned") == "YES":
        return {"level": OWNED, "with": hits or ([ct["name"]] if ct else [])}
    if ct and ct["relation"] == "COMPLEMENTS":
        return {"level": COMPLEMENTS, "with": [ct["name"]]}
    named = list(c.get("overlaps_with", [])) + ([ct["name"]] if ct else [])
    hits = sorted({keys[stack_key(n)]["name"] for n in named if stack_key(n) in keys})
    if hits or c.get("native_overlap") in ("YES", "PARTIAL"):
        return {"level": DUPLICATES, "with": hits}
    if named or ct or c.get("native_overlap") == "NO":
        return {"level": NEW, "with": []}
    return {"level": UNKNOWN, "with": []}


def overlap_points(c, ov):
    """One penalty at most: only a duplicate of the current stack loses points, scaled by native overlap."""
    if ov["level"] != DUPLICATES:
        return 0.0
    return DUPLICATE_POINTS.get(c.get("native_overlap"), DUPLICATE_DEFAULT)


def per_job_fit(c, prof):
    """(job_fit 0..1, matched jobs best-first).

    T = terms(capability + name + job + description); for each profile job j with terms K_j:
      hits_j = |K_j & T|; relevance_j = hits_j / |K_j| if hits_j >= JOB_MIN_HITS else 0
      job_fit = min(1, max_j relevance_j / JOB_FULL_FIT)
    The best single job decides, so a profile with many jobs does not inflate the fit.
    """
    text = " ".join(str(c.get(f)) for f in ("capability", "name", "job", "description") if c.get(f) not in (None, UNKNOWN))
    t = terms(text)
    matched = []
    for job, jt in job_terms(prof):
        hits = sorted(jt & t)
        if len(hits) >= JOB_MIN_HITS:
            matched.append({"job": job, "relevance": round(len(hits) / len(jt), 3), "terms": hits})
    matched.sort(key=lambda m: -m["relevance"])  # stable: profile order breaks ties
    fit = min(1.0, matched[0]["relevance"] / JOB_FULL_FIT) if matched else 0.0
    return round(fit, 3), matched


def score(c, prof, categories, as_of):
    ov = stack_relation(c, prof)
    fit, matched = per_job_fit(c, prof)
    parts = {
        "evidence": EVIDENCE_POINTS[c["evidence_quality"]],
        "source_tier": TIER_POINTS[c["source_tier"]],
        "source_diversity": 0.25 * min(len({url_domain(s["url"]) for s in c["sources"]}), 3),
        "maintenance": STATUS_POINTS[c["status"]],
        "improvement": IMPROVEMENT_POINTS[c["improvement_opportunity"]],
        "job_fit": round(JOB_FIT_POINTS * fit, 3),
        "overlap": overlap_points(c, ov),
    }
    n = popularity_number(c.get("popularity"))
    parts["popularity"] = round(min(POPULARITY_CAP, POPULARITY_CAP * math.log10(n + 1) / 6), 3) if n else 0.0
    lv = parse_date(c["last_verified"])
    fresh = category_by_id(categories, c["category"]).get("freshness_days", 30)
    parts["staleness"] = -0.5 if (lv is None or (as_of - lv).days > fresh) else 0.0
    return round(sum(parts.values()), 3), parts, ov, fit, matched


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


def keeps(c, ov, verdict):
    """Owned and nothing new to adopt: improvement NO (any adopt/try verdict), or USE with improvement UNKNOWN."""
    if ov["level"] != OWNED:
        return False
    imp = c["improvement_opportunity"]
    return (imp == "NO" and verdict in ACTIONABLE) or (imp == UNKNOWN and verdict == "USE")


def derived_verdict(c, ov):
    if c["status"] in ("ARCHIVED", "DEPRECATED"):
        return "IGNORE", f"{c['status'].lower()}"
    if ov["level"] == OWNED and c["improvement_opportunity"] != "YES":
        return "KEEP", "already owned; nothing new to adopt"
    if c["improvement_opportunity"] == "NO" and (c["native_overlap"] == "YES" or ov["level"] == DUPLICATES):
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
    """Live view of a ledger entry: score, verdict (Skill's recommendation capped by evidence), overlap, job fit."""
    c = {"capability": UNKNOWN, "owned": UNKNOWN, **c}  # ledgers written before 0.1.1 lack these fields
    s, parts, ov, fit, matched = score(c, prof, categories, as_of)
    cap, cap_reason = ceiling(c)
    guard = None
    if c.get("recommendation") in RECOMMENDATIONS and not (c["recommendation"] == "KEEP" and ov["level"] != OWNED):
        verdict, source = c["recommendation"], "SKILL"
        reason = c["reason"] if c["reason"] != UNKNOWN else "recommended by scan"
        if keeps(c, ov, verdict):
            guard = f"{verdict} -> KEEP: already owned, nothing new to adopt"
            verdict = "KEEP"
    else:
        if c.get("recommendation") == "KEEP":
            guard = "KEEP needs an owned item; verdict derived instead"
        (verdict, reason), source = derived_verdict(c, ov), "DERIVED"
    if VERDICT_ORDER[verdict] > VERDICT_ORDER[cap]:
        guard = f"{verdict} capped to {cap}: {cap_reason}"
        verdict = cap
    return {**c, "score": s, "score_parts": parts, "stack_overlap": ov, "job_fit": fit, "matched_jobs": matched,
            "verdict": verdict, "verdict_source": source, "verdict_reason": reason, "guard": guard}


def rank(entries, prof, categories, as_of, category=None, top=None, include_ignored=False):
    views = [evaluate(e, prof, categories, as_of) for e in entries
             if category is None or e["category"] == category]
    if not include_ignored:
        views = [v for v in views if v["verdict"] != "IGNORE"]
    views.sort(key=lambda v: (-VERDICT_ORDER[v["verdict"]], -v["score"], v["name"].lower()))
    return views[:top] if top else views


def top_opportunities(entries, prof, categories, as_of, top=10):
    """Products worth changing: improvement YES and verdict USE/TEST (KEEP and IGNORE never qualify)."""
    views = [v for v in rank(entries, prof, categories, as_of)
             if v["improvement_opportunity"] == "YES" and v["verdict"] in ("USE", "TEST")]
    views.sort(key=lambda v: (-v["score"], v["name"].lower()))
    return views[:top]


def _coverage(members):
    if any(v["verdict"] == "KEEP" for v in members):
        return "COVERED"
    if any(v["stack_overlap"]["level"] == OWNED or v["native_overlap"] in ("YES", "PARTIAL") for v in members):
        return "PARTIAL"
    if any(v["native_overlap"] == "NO" or v["stack_overlap"]["level"] == NEW for v in members):
        return "NONE"
    return UNKNOWN


def _weak(v):
    """IGNORE, or a full duplicate of the current stack (a partial native overlap is not enough)."""
    return v["verdict"] == "IGNORE" or (v["stack_overlap"]["level"] == DUPLICATES and v["native_overlap"] == "YES")


def _benchmark(actionable):
    vals = {v["benchmark_needed"] for v in actionable if v["verdict"] in ("USE", "TEST")}
    return "YES" if "YES" in vals else "NO" if "NO" in vals else UNKNOWN


def _group(name, members):
    live = [v for v in members if v["verdict"] != "IGNORE"]
    actionable = sorted((v for v in members if v["verdict"] in ACTIONABLE),
                        key=lambda v: (-VERDICT_ORDER[v["verdict"]], -v["score"], v["name"].lower()))
    coverage = _coverage(members)
    best_ev = max((v["evidence_quality"] for v in actionable), key=EVIDENCE_POINTS.get, default=UNKNOWN)
    imps = {v["improvement_opportunity"] for v in actionable}
    jobs = {}
    for v in live:
        for m in v["matched_jobs"]:
            jobs[m["job"]] = max(jobs.get(m["job"], 0), m["relevance"])
    f = {
        "relevance": max((v["job_fit"] for v in live), default=0.0),
        "gap": COVERAGE_GAP[coverage],
        "credibility": CREDIBILITY[actionable[0]["verdict"]] if actionable else 0.0,
        "evidence": EVIDENCE_POINTS[best_ev] / EVIDENCE_POINTS["STRONG"],
        "improvement": 1.0 if "YES" in imps else 0.5 if UNKNOWN in imps else 0.0,
        "weak_share": sum(1 for v in members if _weak(v)) / len(members),
    }
    opp = round(sum(OPP_WEIGHTS[k] * f[k] for k in OPP_WEIGHTS), 2)
    verdicts = Counter(v["verdict"] for v in members)
    best = actionable[:3]
    matched_jobs = sorted(jobs, key=lambda j: -jobs[j])
    reason = "; ".join(filter(None, [
        f"fits job: {matched_jobs[0]}" if matched_jobs else "matches no profile job",
        {"COVERED": "current stack already covers it (KEEP)", "PARTIAL": "current stack covers it partly",
         "NONE": "not covered by the current stack", UNKNOWN: "current-stack coverage unknown"}[coverage],
        f"best candidate {best[0]['name']} ({best[0]['verdict']}, {best[0]['evidence_quality']} evidence)" if best
        else "no candidate worth adopting",
        "improvement claimed" if f["improvement"] == 1.0 else None,
        f"{f['weak_share']:.0%} of candidates are ignored or duplicate the stack" if f["weak_share"] >= 0.5 else None,
    ]))
    return {
        "capability": name, "key": capability_key(name), "candidate_count": len(members),
        "best_candidates": [{"name": v["name"], "verdict": v["verdict"], "score": v["score"],
                             "evidence_quality": v["evidence_quality"], "benchmark_needed": v["benchmark_needed"]}
                            for v in best],
        "owned": sorted(v["name"] for v in members if v["stack_overlap"]["level"] == OWNED),
        "coverage": coverage,
        "verdicts": {k: verdicts[k] for k in VERDICT_ORDER if verdicts[k]},
        "strongest_verdict": max(verdicts, key=VERDICT_ORDER.get),
        "benchmark_needed": _benchmark(actionable),
        "evidence_strength": best_ev,
        "credible_candidates": sum(1 for v in actionable if v["evidence_quality"] in ("STRONG", "MODERATE")),
        "matched_jobs": matched_jobs,
        "factors": {k: round(x, 3) for k, x in f.items()},
        "opportunity_score": opp,
        "reason": reason,
        "members": sorted(v["name"] for v in members),
    }


def capability_opportunities(entries, prof, categories, as_of, top=None, category=None):
    """Group candidates by `capability` and rank the groups as opportunities for this profile.

    opportunity = 3.0*relevance + 2.5*gap + 2.0*credibility + 1.5*evidence + 1.0*improvement - 1.0*weak_share
      relevance    best job_fit among the group's non-IGNORE candidates (0..1)
      gap          current-stack coverage: NONE 1.0, UNKNOWN 0.75, PARTIAL 0.6, COVERED 0.0
                   (COVERED = an owned candidate is KEEP; PARTIAL = something owned or native overlaps it)
      credibility  best actionable verdict: USE 1.0, TEST 0.75, WATCH 0.25, none 0
      evidence     best evidence quality among USE/TEST/WATCH candidates, STRONG = 1.0
      improvement  1.0 if any USE/TEST/WATCH candidate claims improvement YES, 0.5 if UNKNOWN, else 0
      weak_share   share of the group that is IGNORE or fully duplicates the current stack (native YES)
    Range 0-10. Candidates without a capability are returned separately, never guessed into a group.
    Returns (ranked groups, unassigned candidate views).
    """
    views = [evaluate(e, prof, categories, as_of) for e in entries if category is None or e["category"] == category]
    groups, unassigned = {}, []
    for v in views:
        k = capability_key(v["capability"])
        if k is None:
            unassigned.append(v)
        else:
            groups.setdefault(k, []).append(v)
    out = []
    for members in groups.values():
        spellings = Counter(v["capability"].strip() for v in members)
        name = min(spellings, key=lambda s: (-spellings[s], s))
        out.append(_group(name, members))
    out.sort(key=lambda g: (-g["opportunity_score"], g["key"]))
    unassigned.sort(key=lambda v: v["name"].lower())
    return (out[:top] if top else out), unassigned
