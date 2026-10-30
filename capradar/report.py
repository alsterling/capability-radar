"""Markdown report: TOP N per lane, then top opportunities for the profile."""

from . import __version__
from .core import UNKNOWN
from .rank import rank, top_opportunities
from .reverify import check


def _cell(v, limit=90):
    s = str(v if v not in (None, "") else UNKNOWN).replace("|", "/").replace("\n", " ")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _popularity(p):
    return ", ".join(f"{k}: {v}" for k, v in (p or {}).items()) or UNKNOWN


def _overlap(v):
    ov = v["stack_overlap"]
    out = ov["level"] + (f" ({', '.join(ov['with'])})" if ov["with"] else "")
    if v["native_overlap"] not in ("NO", UNKNOWN):
        out += f"; native {v['native_overlap']}"
    return out


def _details(v):
    srcs = "; ".join(f"{s['url']} ({s['tier']}, {s['type']})" for s in v["sources"]) or "none captured"
    ct = v.get("current_tool")
    rel = f"{ct['relation']} {ct['name']}" if ct else UNKNOWN
    prior = v.get("prior_verdict") or "none"
    rows = [
        ("Job / capability", v["job"]), ("Description", v["description"]), ("Sources", srcs),
        ("Source tier", v["source_tier"]), ("Status / maintenance", f"{v['status']}; last activity {v['last_activity']}"
                                            + (f"; {v['maintenance_notes']}" if v["maintenance_notes"] != UNKNOWN else "")),
        ("Version", v["version"]), ("Popularity / adoption", _popularity(v.get("popularity"))),
        ("Evidence quality", v["evidence_quality"] + (f": {v['evidence_notes']}" if v["evidence_notes"] != UNKNOWN else "")),
        ("Cost", v["cost"]), ("Privacy", v["privacy"]), ("Permissions", v["permissions"]),
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
    lines = ["| # | Name | Verdict | Job / capability | Evidence | Tier | Status | Overlap | Improve | Bench | Score |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, v in enumerate(views, 1):
        lines.append(f"| {i} | {_cell(v['name'], 40)} | {v['verdict']} | {_cell(v['job'], 60)} | {v['evidence_quality']} | "
                     f"{v['source_tier'].split('_')[0]} | {v['status']} | {_cell(_overlap(v), 40)} | "
                     f"{v['improvement_opportunity']} | {v['benchmark_needed']} | {v['score']} |")
    return "\n".join(lines)


def build(ledger, prof, categories, as_of, top=10, only=None, details=True):
    entries = list(ledger["entries"].values())
    cats = [c for c in categories if not only or c["id"] in only]
    out = [f"# Capability Radar report — {as_of.isoformat()}", "",
           f"**Profile:** {prof['name']} · **Ledger entries:** {len(entries)} · **Lanes:** {len(cats)} · "
           f"**capradar** {__version__}", "",
           "Verdicts: **USE** adopt now · **TEST** try it on a real job first · **WATCH** not yet · **IGNORE** skip. "
           "Ranking weighs evidence, source tier and maintenance over popularity; popularity is capped and never "
           "changes a verdict. UNKNOWN means the scan could not establish the value; nothing is guessed.", ""]
    if ledger.get("scans"):
        out += ["**Scans in ledger:** " + "; ".join(
            f"{s['file']} ({s['date']}: {s.get('new', 0)} new, {s.get('merged', 0)} merged)" for s in ledger["scans"]), ""]
    # Summary
    out += ["## Summary", "", "| Lane | Entries | USE | TEST | WATCH | IGNORE |", "|---|---|---|---|---|---|"]
    lane_views = {}
    for c in cats:
        views = rank(entries, prof, categories, as_of, category=c["id"], include_ignored=True)
        lane_views[c["id"]] = views
        n = {k: sum(1 for v in views if v["verdict"] == k) for k in ("USE", "TEST", "WATCH", "IGNORE")}
        out.append(f"| {c['label']} | {len(views)} | {n['USE']} | {n['TEST']} | {n['WATCH']} | {n['IGNORE']} |")
    out.append("")
    # Lanes
    for c in cats:
        views = [v for v in lane_views[c["id"]] if v["verdict"] != "IGNORE"][:top]
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
        if ignored:
            out += ["Ignored: " + "; ".join(f"{v['name']} ({v['verdict_reason']})" for v in ignored), ""]
    # Opportunities
    opps = top_opportunities(entries, prof, categories, as_of, top=top)
    if only:
        opps = [v for v in opps if v["category"] in only]
    out += ["## TOP OPPORTUNITIES FOR THIS PROFILE", ""]
    if opps:
        label = {c["id"]: c["label"] for c in categories}
        for i, v in enumerate(opps, 1):
            out.append(f"{i}. **{v['name']}** ({label[v['category']]}) — {v['verdict']}: {_cell(v['job'], 120)}. "
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
