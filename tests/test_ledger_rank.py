import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from capradar import ledger as L
from capradar import profile as P
from capradar.core import load_categories, normalize_candidate
from capradar.rank import POPULARITY_CAP, evaluate, rank, top_opportunities

FIX = Path(__file__).parent / "fixtures"
CATS = load_categories()
TODAY = date(2026, 1, 15)
PROF = P.load(FIX / "profile.md")


def fixture_ledger():
    led = L.empty()
    for r in json.loads((FIX / "scan_basic.json").read_text(encoding="utf-8"))["candidates"]:
        try:
            c, _ = normalize_candidate(r, CATS, "2026-01-10")
        except ValueError:
            continue
        L.upsert(led, c, "2026-01-10")
    return led


def view(led, name):
    e = next(e for e in led["entries"].values() if e["name"] == name)
    return evaluate(e, PROF, CATS, TODAY)


class Dedupe(unittest.TestCase):
    def test_wrapper_of_same_repo_merges_and_keeps_alias(self):
        led = fixture_ledger()
        mcp = [e for e in led["entries"].values() if e["category"] == "mcp"]
        self.assertEqual(len(mcp), 1)
        self.assertIn("acme-search mcp", mcp[0]["aliases"])
        self.assertEqual(mcp[0]["seen_count"], 2)
        self.assertEqual(mcp[0]["evidence_quality"], "MODERATE", "a later weak duplicate does not erase known values")

    def test_same_name_in_other_lane_is_separate(self):
        led = L.empty()
        for cat in ("mcp", "research_search"):
            L.upsert(led, normalize_candidate({"name": "Acme Search", "category": cat}, CATS)[0], "2026-01-01")
        self.assertEqual(len(led["entries"]), 2)

    def test_duplicate_of_and_alias_lookup(self):
        led = L.empty()
        L.upsert(led, normalize_candidate({"name": "Canonical Tool", "category": "oss"}, CATS)[0], "2026-01-01")
        kind, eid = L.upsert(led, normalize_candidate(
            {"name": "Canonical Tool Fork", "category": "oss", "duplicate_of": "Canonical Tool"}, CATS)[0], "2026-01-02")
        self.assertEqual((kind, eid), ("merged", "oss/canonical"))
        kind, _ = L.upsert(led, normalize_candidate({"name": "canonical tool fork", "category": "oss"}, CATS)[0], "2026-01-03")
        self.assertEqual(kind, "merged", "a remembered alias matches later scans")

    def test_dedupe_command_merges_after_the_fact(self):
        led = L.empty()
        a = normalize_candidate({"name": "Alpha", "category": "oss"}, CATS)[0]
        b = normalize_candidate({"name": "Alpha Two", "category": "oss", "aliases": ["Alpha"]}, CATS)[0]
        led["entries"] = {a["id"]: {**a, "first_seen": "2026-01-01"}, b["id"]: {**b, "first_seen": "2026-01-02"}}
        new, merges = L.dedupe(led)
        self.assertEqual(merges, [("oss/alpha", "oss/alpha-two")])
        self.assertEqual(len(new["entries"]), 1)


class Persistence(unittest.TestCase):
    def test_round_trip_and_verdict_history(self):
        led = fixture_ledger()
        e = next(iter(led["entries"].values()))
        L.record_verdict(e, "WATCH", "2026-01-10")
        L.record_verdict(e, "WATCH", "2026-01-11")
        L.record_verdict(e, "TEST", "2026-01-12")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ledger.json"
            L.save(p, led)
            back = L.load(p)
        e2 = back["entries"][e["id"]]
        self.assertEqual([h["verdict"] for h in e2["verdict_history"]], ["WATCH", "TEST"])
        self.assertEqual((e2["verdict"], e2["prior_verdict"]), ("TEST", "WATCH"))
        self.assertEqual(back["aliases"], led["aliases"])

    def test_newer_known_value_wins_unknown_never_overwrites(self):
        led = L.empty()
        L.upsert(led, normalize_candidate({"name": "T", "category": "oss", "cost": "free", "version": "1.0",
                                           "last_verified": "2026-01-01"}, CATS)[0], "2026-01-01")
        L.upsert(led, normalize_candidate({"name": "T", "category": "oss", "version": "2.0",
                                           "last_verified": "2026-02-01"}, CATS)[0], "2026-02-01")
        e = led["entries"]["oss/t"]
        self.assertEqual((e["cost"], e["version"], e["last_verified"]), ("free", "2.0", "2026-02-01"))


class Ranking(unittest.TestCase):
    def test_four_verdicts_represented(self):
        led = fixture_ledger()
        verdicts = {v["name"]: v["verdict"] for v in rank(led["entries"].values(), PROF, CATS, TODAY, include_ignored=True)}
        self.assertEqual(verdicts["Quiet Eval Harness"], "USE")
        self.assertEqual(verdicts["Acme Search MCP Server"], "TEST")
        self.assertEqual(verdicts["Mystery Tool"], "WATCH")
        self.assertEqual(verdicts["Old Scraper"], "IGNORE")
        self.assertEqual(verdicts["Example Chat Pro"], "IGNORE")

    def test_popularity_cannot_buy_a_verdict_or_beat_evidence(self):
        led = fixture_ledger()
        hyped = view(led, "Hyped Agent Kit")
        self.assertEqual(hyped["verdict"], "TEST", "Skill said USE; anecdotal evidence caps it")
        self.assertIn("capped", hyped["guard"])
        self.assertLessEqual(hyped["score_parts"]["popularity"], POPULARITY_CAP)
        self.assertGreater(view(led, "Quiet Eval Harness")["score"], hyped["score"])

    def test_no_source_caps_at_watch(self):
        c = normalize_candidate({"name": "Bare", "category": "oss", "recommendation": "USE"}, CATS)[0]
        v = evaluate(c, PROF, CATS, TODAY)
        self.assertEqual(v["verdict"], "WATCH")

    def test_stack_overlap(self):
        led = fixture_ledger()
        self.assertEqual(view(led, "Example Chat Pro")["stack_overlap"]["level"], "IN_STACK")
        self.assertEqual(view(led, "Doc Writer Skill")["stack_overlap"],
                         {"level": "OVERLAP", "with": ["Example Chat Pro"]})
        self.assertEqual(view(led, "Mystery Tool")["stack_overlap"]["level"], "UNKNOWN")

    def test_complementing_current_tool_is_not_overlap(self):
        c = normalize_candidate({"name": "Add-on", "category": "skills", "native_overlap": "NO",
                                 "current_tool": {"name": "Example Chat Pro", "relation": "complements"}}, CATS)[0]
        self.assertEqual(evaluate(c, PROF, CATS, TODAY)["stack_overlap"]["level"], "NONE")
        c["current_tool"]["relation"] = "REPLACES"
        self.assertEqual(evaluate(c, PROF, CATS, TODAY)["stack_overlap"]["level"], "OVERLAP")

    def test_top_n_and_category_filter(self):
        led = fixture_ledger()
        allv = rank(led["entries"].values(), PROF, CATS, TODAY)
        self.assertEqual(len(rank(led["entries"].values(), PROF, CATS, TODAY, top=2)), 2)
        self.assertEqual(allv[0]["name"], "Quiet Eval Harness", "USE ranks first")
        self.assertEqual({v["category"] for v in rank(led["entries"].values(), PROF, CATS, TODAY, category="mcp")}, {"mcp"})
        self.assertNotIn("IGNORE", {v["verdict"] for v in allv})

    def test_ranking_is_deterministic(self):
        led = fixture_ledger()
        a = [v["name"] for v in rank(led["entries"].values(), PROF, CATS, TODAY)]
        b = [v["name"] for v in rank(reversed(list(led["entries"].values())), PROF, CATS, TODAY)]
        self.assertEqual(a, b)

    def test_top_opportunities_excludes_in_stack_and_no_improvement(self):
        led = fixture_ledger()
        names = [v["name"] for v in top_opportunities(led["entries"].values(), PROF, CATS, TODAY)]
        self.assertEqual(set(names), {"Quiet Eval Harness", "Acme Search MCP Server", "Doc Writer Skill"})

    def test_nothing_worth_changing_is_empty_not_error(self):
        self.assertEqual(top_opportunities([], PROF, CATS, TODAY), [])


if __name__ == "__main__":
    unittest.main()
