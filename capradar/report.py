"""Markdown reports: TOP N per lane, capability-level opportunities, then product-level opportunities."""

from . import __version__
from .core import UNKNOWN
from .rank import capability_opportunities, rank, top_opportunities
from .reverify import check


def _cell(v, limit=90):
    s = str(v if v not in (None, "") else UNKNOWN).replace("|", "/").replace("\n", " ")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _popularity(p):
    return ", ".join(f"{k}: {v}" for k, v in (p or {}).items()) or UNKNOWN


LEGEND = ("Verdicts: **USE** adopt or start using now · **TEST** try it on a real job first · **WATCH** not yet · "
          "**KEEP** already owned and adequate, nothing to adopt · **IGNORE** skip.")
SHORT = {"ALREADY_OWNED_SAME_CAPABILITY": "OWNED", "COMPLEMENTS_CURRENT_STACK": "COMPLEMENTS",
         "DUPLICATES_CURRENT_STACK": "DUPLICATES", "NEW_CAPABILITY": "NEW"}


def _overlap(v):
    ov = v["stack_overlap"]
    out = SHORT.get(ov["level"], ov["level"]) + (f" ({', '.join(ov['with'])})" if ov["with"] else "")
    if v["native_overlap"] not in ("NO", UNKNOWN):
        out += f"; native {v['native_overlap']}"
    return out


def _details(v):
    srcs = "; ".join(f"{s['url']} ({s['tier']}, {s['type']})" for s in v["sources"]) or "none captured"
    ct = v.get("current_tool")
    rel = f"{ct['relation']} {ct['name']}" if ct else UNKNOWN
    prior = v.get("prior_verdict") or "none"
    jobs = "; ".join(f"{m['job']} ({m['relevance']})" for m in v["matched_jobs"]) or "none"
    rows = [
        ("Capability", v["capability"]), ("Job", v["job"]), ("Description", v["description"]), ("Sources", srcs),
        ("Source tier", v["source_tier"]), ("Status / maintenance", f"{v['status']}; last activity {v['last_activity']}"
                                            + (f"; {v['maintenance_notes']}" if v["maintenance_notes"] != UNKNOWN else "")),
        ("Version", v["version"]), ("Popularity / adoption", _popularity(v.get("popularity"))),
        ("Evidence quality", v["evidence_quality"] + (f": {v['evidence_notes']}" if v["evidence_notes"] != UNKNOWN else "")),
        ("Cost", v["cost"]), ("Privacy", v["privacy"]), ("Permissions", v["permissions"]),
        ("Job fit", f"{v['job_fit']} · matched jobs: {jobs}"),
        ("Current-stack overlap", _overlap(v)), ("Relation to current tool", rel),
        ("Recommendation", f"{v['verdict']} ({v['verdict_source'].lower()}; prior: {prior})"
                           + (f"; guard: {v['guard']}" if v["guard"] else "")),
        ("Reason", v["verdict_reason"]), ("Benchmark needed", v["benchmark_needed"]),
        ("Improvement opportunity", v["improvement_opportunity"]), ("Last verified", v["last_verified"]),
        ("Reverify", f"after {v['reverify_after']}" + (f"; trigger: {v['reverify_trigger']}" if v["reverify_trigger"] != UNKNOWN else "")),
    ]
    if v.get("derived"):
        rows.append(("Derived by policy", ", ".join(v["derived"])))
    return "\n".join(f"- **{k}:** {_cell(val, 600)}" for k, val in rows)


def _table(views):
    lines = ["| # | Name | Verdict | Capability | Evidence | Tier | Status | Overlap | Improve | Bench | Fit | Score |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, v in enumerate(views, 1):
        lines.append(f"| {i} | {_cell(v['name'], 40)} | {v['verdict']} | {_cell(v['capability'], 50)} | {v['evidence_quality']} | "
                     f"{v['source_tier'].split('_')[0]} | {v['status']} | {_cell(_overlap(v), 40)} | "
                     f"{v['improvement_opportunity']} | {v['benchmark_needed']} | {v['job_fit']} | {v['score']} |")
    return "\n".join(lines)


def _cap_table(groups):
    lines = ["| # | Capability | Opportunity | Candidates | Best candidates | Coverage | Verdicts | Benchmark | Evidence |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, g in enumerate(groups, 1):
        best = ", ".join(f"{b['name']} ({b['verdict']})" for b in g["best_candidates"]) or "none"
        verdicts = ", ".join(f"{k} {n}" for k, n in g["verdicts"].items())
        lines.append(f"| {i} | {_cell(g['capability'], 60)} | {g['opportunity_score']} | {g['candidate_count']} | "
                     f"{_cell(best, 120)} | {g['coverage']} | {verdicts} | {g['benchmark_needed']} | {g['evidence_strength']} |")
    return "\n".join(lines)


def _unassigned(views):
    return (["Without a capability (not grouped; the scan did not supply one): "
             + "; ".join(f"{v['name']} ({v['verdict']})" for v in views), ""] if views else [])


def build_capabilities(ledger, prof, categories, as_of, top=10, only=None):
    """Capability-level opportunity report: candidates grouped by `capability`, groups ranked."""
    entries = [e for e in ledger["entries"].values() if not only or e["category"] in only]
    groups, unassigned = capability_opportunities(entries, prof, categories, as_of)
    out = [f"# Capability Radar opportunities — {as_of.isoformat()}", "",
           f"**Profile:** {prof['name']} · **Ledger entries:** {len(entries)} · **Capabilities:** {len(groups)} · "
           f"**capradar** {__version__}", "", LEGEND, "",
           "Opportunity (0–10) = 3.0·relevance + 2.5·coverage gap + 2.0·credibility + 1.5·evidence + 1.0·improvement "
           "− 1.0·weak share. Relevance is the best job fit in the group; the gap is 0 when an owned candidate is KEEP. "
           "Nothing has been installed or benchmarked.", "",
           "## TOP CAPABILITY OPPORTUNITIES", ""]
    if not groups:
        out += ["No capability groups yet (candidates need a `capability` field).", ""]
    else:
        out += [_cap_table(groups[:top]), ""]
        for i, g in enumerate(groups[:top], 1):
            f = g["factors"]
            out += [f"### {i}. {g['capability']}", "",
                    f"- **Opportunity:** {g['opportunity_score']} (relevance {f['relevance']}, gap {f['gap']}, "
                    f"credibility {f['credibility']}, evidence {f['evidence']}, improvement {f['improvement']}, "
                    f"weak share {f['weak_share']})",
                    f"- **Why:** {g['reason']}",
                    f"- **Candidates ({g['candidate_count']}):** {', '.join(g['members'])}",
                    f"- **Best candidates:** " + ("; ".join(
                        f"{b['name']} — {b['verdict']}, {b['evidence_quality']} evidence, benchmark {b['benchmark_needed']}, "
                        f"score {b['score']}" for b in g["best_candidates"]) or "none"),
                    f"- **Current-stack coverage:** {g['coverage']}" + (f" (owned: {', '.join(g['owned'])})" if g["owned"] else ""),
                    f"- **Matched jobs:** {'; '.join(g['matched_jobs']) or 'none'}",
                    f"- **Benchmark needed:** {g['benchmark_needed']} · **Evidence strength:** {g['evidence_strength']} "
                    f"({g['credible_candidates']} candidate(s) MODERATE or STRONG)", ""]
        if len(groups) > top:
            out += ["Lower: " + "; ".join(f"{g['capability']} ({g['opportunity_score']})" for g in groups[top:]), ""]
    out += _unassigned(unassigned)
    return "\n".join(out).rstrip() + "\n"


def build(ledger, prof, categories, as_of, top=10, only=None, details=True):
    entries = list(ledger["entries"].values())
    cats = [c for c in categories if not only or c["id"] in only]
    out = [f"# Capability Radar report — {as_of.isoformat()}", "",
           f"**Profile:** {prof['name']} · **Ledger entries:** {len(entries)} · **Lanes:** {len(cats)} · "
           f"**capradar** {__version__}", "",
           LEGEND + " Ranking weighs evidence, source tier and maintenance over popularity; popularity is capped and never "
           "changes a verdict. UNKNOWN means the scan could not establish the value; nothing is guessed.", ""]
    if ledger.get("scans"):
        out += ["**Scans in ledger:** " + "; ".join(
            f"{s['file']} ({s['date']}: {s.get('new', 0)} new, {s.get('merged', 0)} merged)" for s in ledger["scans"]), ""]
    # Summary
    out += ["## Summary", "", "| Lane | Entries | USE | TEST | WATCH | KEEP | IGNORE |", "|---|---|---|---|---|---|---|"]
    lane_views = {}
    for c in cats:
        views = rank(entries, prof, categories, as_of, category=c["id"], include_ignored=True)
        lane_views[c["id"]] = views
        n = {k: sum(1 for v in views if v["verdict"] == k) for k in ("USE", "TEST", "WATCH", "KEEP", "IGNORE")}
        out.append(f"| {c['label']} | {len(views)} | {n['USE']} | {n['TEST']} | {n['WATCH']} | {n['KEEP']} | {n['IGNORE']} |")
    out.append("")
    # Lanes
    for c in cats:
        views = [v for v in lane_views[c["id"]] if v["verdict"] not in ("IGNORE", "KEEP")][:top]
        kept = [v for v in lane_views[c["id"]] if v["verdict"] == "KEEP"]
        ignored = [v for v in lane_views[c["id"]] if v["verdict"] == "IGNORE"]
        out += [f"## TOP {top} {c['label'].upper()}", ""]
        if not views:
            out += ["No ranked candidates in this lane yet." if not lane_views[c["id"]]
                    else "Nothing worth changing in this lane.", ""]
        else:
            out += [_table(views), ""]
            if details:
                for i, v in enumerate(views, 1):
                    out += [f"### {i}. {v['name']}", "", _details(v), ""]
        if kept:
            out += ["Keep (already owned, nothing new to adopt): " + "; ".join(
                f"{v['name']}" + (f" ({v['guard']})" if v["guard"] else "") for v in kept), ""]
        if ignored:
            out += ["Ignored: " + "; ".join(f"{v['name']} ({v['verdict_reason']})" for v in ignored), ""]
    # Capability opportunities
    groups, unassigned = capability_opportunities([e for e in entries if not only or e["category"] in only],
                                                  prof, categories, as_of, top=top)
    out += ["## TOP CAPABILITY OPPORTUNITIES", ""]
    out += ([_cap_table(groups), "", "Details per capability: `capradar opportunities`.", ""] if groups
            else ["No capability groups yet (candidates need a `capability` field).", ""])
    out += _unassigned(unassigned)
    # Product opportunities
    opps = top_opportunities(entries, prof, categories, as_of, top=top)
    if only:
        opps = [v for v in opps if v["category"] in only]
    out += ["## TOP PRODUCT OPPORTUNITIES FOR THIS PROFILE", ""]
    if opps:
        label = {c["id"]: c["label"] for c in categories}
        for i, v in enumerate(opps, 1):
            out.append(f"{i}. **{v['name']}** ({label[v['category']]}; capability: {v['capability']}) — {v['verdict']}: "
                       f"{_cell(v['job'], 120)}. "
                       f"{_cell(v['verdict_reason'], 160)} Benchmark needed: {v['benchmark_needed']}.")
        out.append("")
    else:
        out += ["Nothing worth changing right now. That is a valid result.", ""]
    # Reverify
    rv = check(ledger, categories, as_of)
    out += ["## Reverify", "",
            f"Stale: {len(rv['stale'])} · Due: {len(rv['due'])} · Trigger watch: {len(rv['trigger_watch'])} · "
            f"Lanes needing a fresh scan: {', '.join(r['label'] for r in rv['categories_needing_scan']) or 'none'}", ""]
    return "\n".join(out).rstrip() + "\n"
