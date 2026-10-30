"""Durable JSON ledger: every candidate ever seen, its aliases, verdict history and evidence."""

import copy
import json
from pathlib import Path

from .core import TIERS, UNKNOWN, best_tier, candidate_keys, name_key, parse_date

SCHEMA = "capradar.ledger/1"
# Fields where a newer, known value replaces the older one. UNKNOWN never overwrites a known value.
SCALAR_FIELDS = ("capability", "owned", "job", "description", "cost", "privacy", "permissions", "reason", "version",
                 "evidence_notes", "reverify_trigger", "maintenance_notes", "recommendation", "improvement_opportunity",
                 "benchmark_needed", "native_overlap", "evidence_quality", "status", "last_activity",
                 "last_verified", "reverify_after", "popularity", "current_tool", "repo")


def empty():
    return {"schema": SCHEMA, "entries": {}, "aliases": {}, "scans": []}


def load(path):
    p = Path(path)
    if not p.exists():
        return empty()
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{p}: not a {SCHEMA} ledger")
    return data


def save(path, ledger):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(p)


def _alias_index_keys(c):
    keys = candidate_keys(c)
    if c.get("duplicate_of"):
        keys.add(f"name:{name_key(c['duplicate_of'])}")
    return {f"{c['category']}::{k}" for k in keys}


def find_match(ledger, c):
    """Existing entry id for this candidate (same category; shared name, alias, repo or duplicate_of)."""
    if c["id"] in ledger["entries"]:
        return c["id"]
    for k in sorted(_alias_index_keys(c)):
        hit = ledger["aliases"].get(k)
        if hit in ledger["entries"]:
            return hit
    return None


def _register(ledger, entry_id):
    e = ledger["entries"][entry_id]
    for k in sorted(_alias_index_keys(e)):  # sorted: ledger.json must not depend on the hash seed
        ledger["aliases"].setdefault(k, entry_id)


def _known(v):
    return v not in (None, UNKNOWN, "", {}, [])


def merge(existing, incoming):
    """Merge incoming into existing in place. The more recently verified record wins on known values.

    On a same-day tie the incoming record wins only if its best source tier is at least as strong, so a
    community wrapper never overwrites what an official source established.
    """
    floor = parse_date("0001-01-01")
    d_in = parse_date(incoming.get("last_verified")) or floor
    d_ex = parse_date(existing.get("last_verified")) or floor
    newer = d_in > d_ex or (d_in == d_ex and TIERS.index(incoming.get("source_tier", UNKNOWN))
                                             <= TIERS.index(existing.get("source_tier", UNKNOWN)))
    for f in SCALAR_FIELDS:
        if _known(incoming.get(f)) and (newer or not _known(existing.get(f))):
            existing[f] = incoming[f]
    urls = {s["url"] for s in existing.get("sources", [])}
    existing.setdefault("sources", []).extend(s for s in incoming.get("sources", []) if s["url"] not in urls)
    names = set(existing.get("aliases", [])) | set(incoming.get("aliases", []))
    if incoming["name"] != existing["name"]:
        names.add(incoming["name"])
    existing["aliases"] = sorted(names - {existing["name"]})
    existing["overlaps_with"] = sorted(set(existing.get("overlaps_with", [])) | set(incoming.get("overlaps_with", [])))
    existing["derived"] = sorted(set(existing.get("derived", [])) | set(incoming.get("derived", [])))
    existing["source_tier"] = best_tier(existing["sources"])
    existing["seen_count"] = existing.get("seen_count", 1) + incoming.get("seen_count", 1)
    for h in incoming.get("verdict_history", []):
        if h not in existing.setdefault("verdict_history", []):
            existing["verdict_history"].append(h)
    existing["verdict_history"].sort(key=lambda h: h["date"])
    return existing


def record_verdict(entry, verdict, on):
    """Append to verdict history when the verdict changes; keep prior_verdict for the report."""
    hist = entry.setdefault("verdict_history", [])
    if not hist or hist[-1]["verdict"] != verdict:
        entry["prior_verdict"] = hist[-1]["verdict"] if hist else None
        hist.append({"date": str(on), "verdict": verdict})
    entry["verdict"] = verdict


def upsert(ledger, c, on):
    """Insert or merge a normalized candidate. Returns ("new" | "merged", entry_id)."""
    hit = find_match(ledger, c)
    if hit:
        merge(ledger["entries"][hit], c)
        _register(ledger, hit)
        return "merged", hit
    c = copy.deepcopy(c)
    c.setdefault("first_seen", str(on))
    c.setdefault("seen_count", 1)
    c.setdefault("verdict_history", [])
    ledger["entries"][c["id"]] = c
    _register(ledger, c["id"])
    return "new", c["id"]


def dedupe(ledger):
    """Rebuild the ledger from its own entries, oldest first, merging any duplicates found.

    Returns (new_ledger, merges) where merges is a list of (kept_id, merged_id).
    """
    out = empty()
    out["scans"] = ledger.get("scans", [])
    merges = []
    for eid, e in sorted(ledger["entries"].items(), key=lambda kv: (kv[1].get("first_seen", ""), kv[0])):
        kind, kept = upsert(out, copy.deepcopy(e), e.get("first_seen", ""))
        if kind == "merged":
            merges.append((kept, eid))
    return out, merges
