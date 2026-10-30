"""Find what needs re-verification. No scheduling: run it whenever you like."""

from .core import UNKNOWN, category_by_id, parse_date


def check(ledger, categories, as_of):
    stale, due, triggers = [], [], []
    newest = {}
    for e in ledger["entries"].values():
        cat = category_by_id(categories, e["category"]) if any(c["id"] == e["category"] for c in categories) else {}
        fresh = cat.get("freshness_days", 30)
        lv = parse_date(e.get("last_verified"))
        age = (as_of - lv).days if lv else None
        row = {"id": e["id"], "name": e["name"], "category": e["category"], "last_verified": e.get("last_verified", UNKNOWN),
               "age_days": age, "freshness_days": fresh, "verdict": e.get("verdict")}
        if lv is None:
            stale.append({**row, "reason": "never verified"})
        elif age > fresh:
            stale.append({**row, "reason": f"verified {age}d ago > {fresh}d window"})
        ra = parse_date(e.get("reverify_after"))
        if ra and ra <= as_of:
            due.append({**row, "reverify_after": ra.isoformat(), "reason": "reverify date reached"})
        if e.get("reverify_trigger") not in (None, "", UNKNOWN):
            triggers.append({**row, "trigger": e["reverify_trigger"]})
        if lv and (e["category"] not in newest or lv > newest[e["category"]]):
            newest[e["category"]] = lv
    needs_scan = []
    for c in categories:
        lv = newest.get(c["id"])
        if lv is None:
            needs_scan.append({"category": c["id"], "label": c["label"], "reason": "no verified entries"})
        elif (as_of - lv).days > c.get("freshness_days", 30):
            needs_scan.append({"category": c["id"], "label": c["label"],
                               "reason": f"newest verification {lv.isoformat()} is older than {c.get('freshness_days', 30)}d"})
    return {"as_of": as_of.isoformat(), "stale": stale, "due": due, "trigger_watch": triggers,
            "categories_needing_scan": needs_scan,
            "needs_fresh_scan": sorted({r["id"] for r in stale + due})}


def to_text(result):
    lines = [f"Reverify check as of {result['as_of']}"]
    for key, title in (("stale", "STALE"), ("due", "DUE"), ("trigger_watch", "TRIGGER WATCH")):
        rows = result[key]
        lines.append(f"\n{title} ({len(rows)})")
        for r in rows:
            extra = r.get("trigger") or r.get("reason")
            lines.append(f"  - [{r['category']}] {r['name']}: {extra}")
    lines.append(f"\nCATEGORIES NEEDING A FRESH SCAN ({len(result['categories_needing_scan'])})")
    for r in result["categories_needing_scan"]:
        lines.append(f"  - {r['label']}: {r['reason']}")
    if not (result["stale"] or result["due"] or result["categories_needing_scan"]):
        lines.append("\nNothing stale or due.")
    return "\n".join(lines)
