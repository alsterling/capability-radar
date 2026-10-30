import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

from capradar import cli
from capradar import ledger as L
from capradar import profile as P
from capradar import report as R
from capradar import reverify as V
from capradar.core import load_categories, normalize_candidate

FIX = Path(__file__).parent / "fixtures"
CATS = load_categories()
ROOT = Path(__file__).resolve().parents[1]


def run(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(list(argv))
    return code, buf.getvalue()


def entry(name, cat, **kw):
    return normalize_candidate({"name": name, "category": cat, **kw}, CATS)[0]


class Reverify(unittest.TestCase):
    def setUp(self):
        self.led = L.empty()
        for c in (entry("Fresh", "mcp", last_verified="2026-01-10", reverify_after="2026-03-01"),
                  entry("Old", "mcp", last_verified="2025-06-01", reverify_after="2026-03-01"),
                  entry("Never", "oss"),
                  entry("Due", "models", last_verified="2026-01-05", reverify_after="2026-01-12"),
                  entry("Watched", "skills", last_verified="2026-01-10", reverify_trigger="vendor ships v2")):
            L.upsert(self.led, c, "2026-01-10")
        self.r = V.check(self.led, CATS, date(2026, 1, 15))

    def test_stale_due_trigger(self):
        self.assertEqual({x["name"] for x in self.r["stale"]}, {"Old", "Never"})
        self.assertEqual([x["name"] for x in self.r["due"]], ["Due"])
        self.assertEqual([x["trigger"] for x in self.r["trigger_watch"]], ["vendor ships v2"])
        self.assertEqual(set(self.r["needs_fresh_scan"]), {"mcp/old", "oss/never", "models/due"})

    def test_lanes_needing_scan(self):
        lanes = {x["category"] for x in self.r["categories_needing_scan"]}
        self.assertEqual(lanes, {"plugins_connectors", "agents", "oss", "research_search", "automation"})
        later = V.check(self.led, CATS, date(2026, 6, 1))
        self.assertIn("mcp", {x["category"] for x in later["categories_needing_scan"]})

    def test_text_output(self):
        self.assertIn("STALE (2)", V.to_text(self.r))


class Report(unittest.TestCase):
    def setUp(self):
        self.prof = P.load(FIX / "profile.md")
        self.led = L.empty()
        for r in json.loads((FIX / "scan_basic.json").read_text(encoding="utf-8"))["candidates"]:
            try:
                L.upsert(self.led, normalize_candidate(r, CATS, "2026-01-10")[0], "2026-01-10")
            except ValueError:
                pass

    def test_all_lanes_and_opportunities(self):
        md = R.build(self.led, self.prof, CATS, date(2026, 1, 15), top=10)
        for label in ("SKILLS", "PLUGINS / CONNECTORS", "MCPS", "AGENTS / PERSISTENT WORKERS", "GITHUB / OSS PROJECTS",
                      "MODELS / NATIVE FEATURES", "RESEARCH / SEARCH TOOLS", "AUTOMATION / WORKFLOW TOOLS"):
            self.assertIn(f"## TOP 10 {label}", md)
        self.assertIn("## TOP OPPORTUNITIES FOR THIS PROFILE", md)
        self.assertIn("Quiet Eval Harness", md)
        self.assertIn("**Improvement opportunity:** UNKNOWN", md, "unknown fields shown as UNKNOWN")
        self.assertIn("Ignored: ", md)
        self.assertIn("guard: USE capped to TEST", md)

    def test_category_filter_and_empty_result(self):
        md = R.build(self.led, self.prof, CATS, date(2026, 1, 15), top=3, only=["mcp"])
        self.assertEqual(re.findall(r"^## TOP 3 (.+)$", md, re.M), ["MCPS"])
        empty = R.build(L.empty(), self.prof, CATS, date(2026, 1, 15))
        self.assertIn("Nothing worth changing right now", empty)


class Cli(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            ws = str(Path(d) / "radar")
            self.assertEqual(run("init", "--dir", ws, "--example")[0], 0)
            self.assertEqual(run("init", "--dir", ws)[0], 1, "init never clobbers an existing workspace")
            self.assertIn("synthetic", (Path(ws) / "profile.md").read_text(encoding="utf-8"))
            code, out = run("scan", "--dir", ws, "--category", "mcp", "--category", "skills", "--as-of", "2026-01-10")
            plan = json.loads((Path(ws) / "inbox/scan-plan-2026-01-10.json").read_text(encoding="utf-8"))
            self.assertEqual([l["id"] for l in plan["lanes"]], ["skills", "mcp"])
            self.assertIn("candidate_contract", plan)
            code, out = run("ingest", "--dir", ws, str(FIX / "scan_basic.json"), "--as-of", "2026-01-15")
            self.assertEqual(code, 1, "rejected candidates are reported")
            self.assertIn("7 new, 1 merged, 2 rejected", out)
            code, out = run("dedupe", "--dir", ws, "--dry-run")
            self.assertIn("0 duplicate(s)", out)
            code, out = run("rank", "--dir", ws, "--json", "--as-of", "2026-01-15")
            ranked = json.loads(out)
            self.assertEqual(len(ranked), 8)
            self.assertEqual(ranked["oss"][0]["verdict"], "USE")
            code, out = run("report", "--dir", ws, "--as-of", "2026-01-15")
            self.assertTrue((Path(ws) / "reports/radar-2026-01-15.md").is_file())
            code, out = run("reverify", "--dir", ws, "--as-of", "2026-06-01", "--write-plan")
            self.assertIn("STALE", out)
            led = L.load(Path(ws) / "ledger.json")
            self.assertEqual(led["scans"][0]["new"], 7)
            self.assertTrue(all(e["verdict_history"] for e in led["entries"].values()))
            # second ingest of the same scan only merges
            code, out = run("ingest", "--dir", ws, str(FIX / "scan_basic.json"), "--as-of", "2026-01-15")
            self.assertIn("0 new, 8 merged", out)

    def test_missing_workspace_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as cm:
                run("rank", "--dir", str(Path(d) / "nope"))
            self.assertIn("no radar workspace", str(cm.exception))


class PublicSafety(unittest.TestCase):
    """The package must stay generic: no personal data, no benchmark-specific hardcoding, no network code."""

    def shipped_files(self):
        skip = {"tests", ".git", "radar", "__pycache__"}
        return [p for p in ROOT.rglob("*") if p.is_file() and not (set(p.relative_to(ROOT).parts) & skip)
                and p.suffix in {".py", ".md", ".json", ".toml", ".txt", ""}]

    def test_no_private_markers(self):
        markers = [bytes.fromhex(h).decode() for h in (
            "41495f457865637574696f6e5f53797374656d",  # private repo name
            "616c737465726c696e67",                    # account handle
            "40676d61696c2e636f6d",                    # personal mail domain
            "44617465204e69676874",                    # earlier private benchmark fixture
        )]
        squash = lambda s: re.sub(r"[\s_\-/\\]", "", s.lower())  # catch AI-Execution, ai_execution, paths...
        markers = [squash(m) for m in markers] + ["appdatalocaltemp", "c:users"]
        hits = [(p.name, m) for p in self.shipped_files() for m in markers
                if m in squash(p.read_text(encoding="utf-8", errors="ignore"))]
        self.assertEqual(hits, [])

    def test_no_network_code_in_cli(self):
        for p in (ROOT / "capradar").glob("*.py"):
            text = p.read_text(encoding="utf-8")
            for mod in ("urllib.request", "http.client", "import socket", "import requests", "urlopen"):
                self.assertNotIn(mod, text, f"{p.name} imports {mod}")

    def test_no_candidate_names_hardcoded_in_code(self):
        names = set()
        for scan in [FIX / "scan_basic.json", *(ROOT / "examples").glob("*.json")]:
            data = json.loads(scan.read_text(encoding="utf-8"))
            names |= {c["name"] for c in (data.get("candidates", []) if isinstance(data, dict) else data) if c.get("name")}
        code = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "capradar").glob("*.py")).lower()
        self.assertEqual(sorted(n for n in names if len(n) > 3 and n.lower() in code), [])


if __name__ == "__main__":
    unittest.main()
