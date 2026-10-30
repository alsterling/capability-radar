"""capradar CLI: init, scan (plan), ingest, dedupe, rank, report, reverify."""

import argparse
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

from . import __version__, ledger as L, profile as P, report as R, reverify as V
from .core import (DATE_FIELDS, ENUM_FIELDS, PKG_DATA, SOURCE_TYPES, TEXT_FIELDS, TIERS, load_categories,
                   normalize_candidate, resolve_category)
from .rank import evaluate, rank


class Workspace:
    def __init__(self, root):
        self.root = Path(root)
        self.profile = self.root / "profile.md"
        self.config = self.root / "config.json"
        self.ledger = self.root / "ledger.json"
        self.inbox = self.root / "inbox"
        self.reports = self.root / "reports"

    def require(self):
        if not self.ledger.exists():
            raise SystemExit(f"no radar workspace at {self.root} (run: python -m capradar init --dir {self.root})")

    def categories(self):
        cfg = json.loads(self.config.read_text(encoding="utf-8")) if self.config.exists() else {}
        return load_categories(cfg)


def _write(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def _cats(ws, values):
    cats = ws.categories()
    return [resolve_category(v, cats) for v in values] if values else None


def cmd_init(ws, a):
    if ws.ledger.exists() and not a.force:
        print(f"workspace already exists at {ws.root} (use --force to reset profile/config; the ledger is kept)")
        return 1
    ws.root.mkdir(parents=True, exist_ok=True)
    for d in (ws.inbox, ws.reports):
        d.mkdir(exist_ok=True)
    src = PKG_DATA / ("profile.example.md" if a.example else "profile.template.md")
    shutil.copyfile(src, ws.profile)
    cfg = {"version": __version__, "top_n": 10,
           "categories": json.loads((PKG_DATA / "categories.json").read_text(encoding="utf-8"))["categories"]}
    _write(ws.config, json.dumps(cfg, indent=2) + "\n")
    if not ws.ledger.exists():
        L.save(ws.ledger, L.empty())
    print(f"initialized {ws.root}\n  edit {ws.profile} (jobs, current stack, constraints)\n"
          f"  then run a scan: /capability-radar:scan  or  python -m capradar scan --all")
    return 0


def contract():
    return {
        "required": ["name", "category"],
        "text_fields": list(TEXT_FIELDS),
        "enum_fields": {k: list(v) for k, v in ENUM_FIELDS.items()},
        "date_fields": list(DATE_FIELDS),
        "sources": {"url": "required", "tier": list(TIERS), "type": list(SOURCE_TYPES), "accessed": "YYYY-MM-DD"},
        "other": {"popularity": "object, e.g. {\"stars\": 1200, \"downloads\": \"UNKNOWN\"}",
                  "aliases": "list of other names / wrappers / forks", "overlaps_with": "list of tools it duplicates",
                  "duplicate_of": "name of the canonical candidate if this is a wrapper/fork",
                  "current_tool": "{\"name\": ..., \"relation\": REPLACES|COMPLEMENTS|DUPLICATES|BEATS|LOSES_TO}",
                  "repo": "the candidate's own repository URL, if any"},
        "rule": "Use UNKNOWN for anything you could not verify. Never guess.",
    }


def cmd_scan(ws, a):
    """Write a scan plan for the Skill: lanes, profile, what is already known, what to re-verify."""
    ws.require()
    cats = ws.categories()
    wanted = _cats(ws, a.category) or [c["id"] for c in cats]
    prof = P.load(ws.profile)
    led = L.load(ws.ledger)
    today = a.as_of
    known = {cid: sorted(e["name"] for e in led["entries"].values() if e["category"] == cid) for cid in wanted}
    rv = V.check(led, cats, today)
    out = f"inbox/scan-{today.isoformat()}.json"  # relative to the workspace: plans never embed local paths
    plan = {
        "scan_plan": f"capradar {__version__}", "date": today.isoformat(), "top": a.top,
        "lanes": [{"id": c["id"], "label": c["label"]} for c in cats if c["id"] in wanted],
        "profile": {"name": prof["name"], "jobs": prof["jobs"], "current_stack": prof["stack"], "constraints": prof["constraints"]},
        "already_in_ledger": known,
        "reverify": [r for r in rv["stale"] + rv["due"] if r["category"] in wanted],
        "workspace": "the folder given by --dir (default ./radar)",
        "write_candidates_to": out,
        "candidate_contract": contract(),
        "then_run": [f"python -m capradar ingest <workspace>/{out}", f"python -m capradar report --top {a.top}",
                     "python -m capradar reverify"],
    }
    plan_path = ws.inbox / f"scan-plan-{today.isoformat()}.json"
    _write(plan_path, json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    print(f"scan plan: {plan_path}\nlanes: {', '.join(l['label'] for l in plan['lanes'])}\n"
          f"next: research each lane (the Skill does this), write candidates to {ws.root / out}, then ingest")
    return 0


def _read_scan(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {}, data
    return data.get("scan", {}), data.get("candidates", [])


def cmd_ingest(ws, a):
    ws.require()
    cats = ws.categories()
    prof = P.load(ws.profile)
    led = L.load(ws.ledger)
    rejected = 0
    for path in a.files:
        meta, raws = _read_scan(path)
        scan_date = meta.get("date") or a.as_of.isoformat()
        counts = {"new": 0, "merged": 0, "rejected": 0}
        for i, raw in enumerate(raws):
            try:
                c, warns = normalize_candidate(raw, cats, scan_date)
            except ValueError as e:
                counts["rejected"] += 1
                print(f"  REJECTED #{i} {raw.get('name', '?') if isinstance(raw, dict) else '?'}: {e}")
                continue
            for w in warns:
                print(f"  warn {c['name']}: {w}")
            kind, eid = L.upsert(led, c, scan_date)
            counts[kind] += 1
            v = evaluate(led["entries"][eid], prof, cats, a.as_of)
            L.record_verdict(led["entries"][eid], v["verdict"], scan_date)
        led["scans"].append({"date": scan_date, "file": Path(path).name, **counts})
        rejected += counts["rejected"]
        print(f"{Path(path).name}: {counts['new']} new, {counts['merged']} merged, {counts['rejected']} rejected")
    L.save(ws.ledger, led)
    print(f"ledger: {len(led['entries'])} entries -> {ws.ledger}")
    return 1 if rejected else 0


def cmd_dedupe(ws, a):
    ws.require()
    led, merges = L.dedupe(L.load(ws.ledger))
    for kept, gone in merges:
        print(f"  merged {gone} -> {kept}")
    if not a.dry_run:
        L.save(ws.ledger, led)
    print(f"{len(merges)} duplicate(s) {'found' if a.dry_run else 'merged'}; {len(led['entries'])} entries")
    return 0


def cmd_rank(ws, a):
    ws.require()
    cats = ws.categories()
    prof = P.load(ws.profile)
    entries = list(L.load(ws.ledger)["entries"].values())
    wanted = _cats(ws, a.category) or [c["id"] for c in cats]
    result = {}
    for cid in wanted:
        result[cid] = rank(entries, prof, cats, a.as_of, category=cid, top=a.top, include_ignored=a.include_ignored)
    if a.json:
        print(json.dumps({k: [{"name": v["name"], "verdict": v["verdict"], "score": v["score"], "guard": v["guard"]}
                              for v in vs] for k, vs in result.items()}, indent=2))
        return 0
    label = {c["id"]: c["label"] for c in cats}
    for cid, views in result.items():
        print(f"\nTOP {a.top} {label[cid].upper()}")
        if not views:
            print("  (none)")
        for i, v in enumerate(views, 1):
            print(f"  {i:>2}. {v['verdict']:<6} {v['score']:>6}  {v['name']}" + (f"  [{v['guard']}]" if v["guard"] else ""))
    return 0


def cmd_report(ws, a):
    ws.require()
    cats = ws.categories()
    text = R.build(L.load(ws.ledger), P.load(ws.profile), cats, a.as_of, top=a.top,
                   only=_cats(ws, a.category), details=not a.no_details)
    out = Path(a.out) if a.out else ws.reports / f"radar-{a.as_of.isoformat()}.md"
    _write(out, text)
    print(f"report: {out}")
    return 0


def cmd_reverify(ws, a):
    ws.require()
    result = V.check(L.load(ws.ledger), ws.categories(), a.as_of)
    if a.write_plan:
        p = ws.inbox / f"reverify-plan-{a.as_of.isoformat()}.json"
        _write(p, json.dumps(result, indent=2) + "\n")
        print(f"reverify plan: {p}")
    print(json.dumps(result, indent=2) if a.json else V.to_text(result))
    return 0


def build_parser():
    ap = argparse.ArgumentParser(prog="capradar", description="Capability Radar: rank and re-verify AI capabilities.")
    ap.add_argument("--version", action="version", version=f"capradar {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dir", default=os.environ.get("CAPRADAR_HOME", "radar"), help="workspace (default ./radar or $CAPRADAR_HOME)")
    common.add_argument("--as-of", type=date.fromisoformat, default=date.today(), help="date to evaluate as (YYYY-MM-DD)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", parents=[common], help="create a workspace")
    p.add_argument("--example", action="store_true", help="start from the synthetic example profile")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("scan", parents=[common], help="write a scan plan for the Skill")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="all lanes (default)")
    g.add_argument("--category", action="append", help="lane id/label; repeatable")
    p.add_argument("--top", type=int, default=10)
    p.set_defaults(fn=cmd_scan)

    p = sub.add_parser("ingest", parents=[common], help="add candidate JSON to the ledger")
    p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser("dedupe", parents=[common], help="merge duplicate ledger entries")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_dedupe)

    for name, fn, hlp in (("rank", cmd_rank, "print top-N per lane"), ("report", cmd_report, "write the Markdown report")):
        p = sub.add_parser(name, parents=[common], help=hlp)
        p.add_argument("--category", action="append", help="lane id/label; repeatable")
        p.add_argument("--top", type=int, default=10)
        p.set_defaults(fn=fn)
    sub.choices["rank"].add_argument("--json", action="store_true")
    sub.choices["rank"].add_argument("--include-ignored", action="store_true")
    sub.choices["report"].add_argument("--out")
    sub.choices["report"].add_argument("--no-details", action="store_true")

    p = sub.add_parser("reverify", parents=[common], help="list stale / due entries and lanes needing a fresh scan")
    p.add_argument("--json", action="store_true")
    p.add_argument("--write-plan", action="store_true")
    p.set_defaults(fn=cmd_reverify)
    return ap


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    a = build_parser().parse_args(argv)
    return a.fn(Workspace(a.dir), a)
