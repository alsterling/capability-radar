"""0.1.1: capability field, KEEP, current-stack relation, per-job job_fit, capability ranking, idempotent ingest."""

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

from capradar import cli
from capradar import ledger as L
from capradar import profile as P
from capradar import report as R
from capradar.core import UNKNOWN, capability_key, load_categories, normalize_candidate
from capradar.rank import (COMPLEMENTS, DUPLICATES, JOB_FIT_POINTS, NEW, OWNED, capability_opportunities, evaluate,
                           per_job_fit, rank)

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"
FIRST = ROOT / "examples" / "first-real-scan-2026-10-30"
RERANK = ROOT / "examples" / "first-real-scan-2026-10-30-rerank-v0.1.1"
CATS = load_categories()
TODAY = date(2026, 1, 15)
PROF = P.parse("""# Two-job profile
## Jobs
- research questions and write cited briefs with verifiable sources
- turn rough meeting notes into clear documents
## Current stack
- Example Chat Pro | models | chat, research
""")
SRC = [{"url": "https://docs.example.org/x", "tier": "TIER1_OFFICIAL", "type": "docs"}]


def cand(name, **kw):
    return normalize_candidate({"name": name, "category": kw.pop("category", "oss"), "sources": SRC, **kw},
                               CATS, "2026-01-10")[0]


def ev(c, prof=PROF):
    return evaluate(c, prof, CATS, TODAY)


def run(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(list(argv))
    return code, buf.getvalue()


class CapabilityField(unittest.TestCase):
    def test_capability_is_separate_from_name(self):
        c = cand("Some Product", capability="  web search with citations ")
        self.assertEqual((c["name"], c["capability"]), ("Some Product", "web search with citations"))
        self.assertEqual(ev(c)["capability"], "web search with citations")

    def test_missing_capability_stays_unknown(self):
        c = cand("Bare Product", job="convert documents to markdown")
        self.assertEqual(c["capability"], UNKNOWN, "never inferred from job, name or description")
        groups, unassigned = capability_opportunities([c], PROF, CATS, TODAY)
        self.assertEqual(groups, [])
        self.assertEqual([v["name"] for v in unassigned], ["Bare Product"])

    def test_capability_key_ignores_case_and_punctuation(self):
        self.assertEqual(capability_key("Web research, with citations"), capability_key("web research with  citations"))
        self.assertIsNone(capability_key(UNKNOWN))

    def test_ledger_merge_keeps_known_capability(self):
        led = L.empty()
        L.upsert(led, cand("Tool", capability="note taking"), "2026-01-10")
        L.upsert(led, cand("Tool"), "2026-01-11")
        self.assertEqual(led["entries"]["oss/tool"]["capability"], "note taking")

    def test_old_ledger_entries_without_capability_still_evaluate(self):
        c = cand("Legacy")
        del c["capability"], c["owned"]
        self.assertEqual(ev(c)["capability"], UNKNOWN)


class StackRelation(unittest.TestCase):
    def test_owned_same_capability_by_name_or_flag(self):
        self.assertEqual(ev(cand("Example Chat Pro"))["stack_overlap"]["level"], OWNED)
        v = ev(cand("Built-in Feature", owned="yes", native_overlap="YES", overlaps_with=["Example Chat Pro"]))
        self.assertEqual(v["stack_overlap"]["level"], OWNED)
        self.assertEqual(v["score_parts"]["overlap"], 0.0, "owned: no native or stack penalty")

    def test_wrapper_named_after_a_stack_item_is_not_owned(self):
        v = ev(cand("Example Chat Pro MCP Server", native_overlap="YES", overlaps_with=["Example Chat Pro"]))
        self.assertEqual(v["stack_overlap"], {"level": DUPLICATES, "with": ["Example Chat Pro"]})
        self.assertEqual(ev(cand("example-chat pro"))["stack_overlap"]["level"], OWNED, "case and punctuation still match")

    def test_complement_has_no_overlap_penalty(self):
        v = ev(cand("Plugin", native_overlap="YES", overlaps_with=["Example Chat Pro"],
                    current_tool={"name": "Example Chat Pro", "relation": "COMPLEMENTS"}))
        self.assertEqual(v["stack_overlap"]["level"], COMPLEMENTS)
        self.assertEqual(v["score_parts"]["overlap"], 0.0)

    def test_duplicate_is_penalized_once(self):
        full = ev(cand("Clone", native_overlap="YES", overlaps_with=["Example Chat Pro"],
                       current_tool={"name": "Example Chat Pro", "relation": "DUPLICATES"}))
        self.assertEqual(full["stack_overlap"], {"level": DUPLICATES, "with": ["Example Chat Pro"]})
        self.assertEqual(full["score_parts"]["overlap"], -1.5, "one penalty, not native -1.5 plus stack -1.0")
        self.assertNotIn("native_overlap", full["score_parts"])
        self.assertEqual(ev(cand("Named", overlaps_with=["Example Chat Pro"]))["score_parts"]["overlap"], -1.0)
        self.assertEqual(ev(cand("Partial", native_overlap="PARTIAL"))["score_parts"]["overlap"], -0.5)

    def test_new_capability_has_no_penalty(self):
        v = ev(cand("Novel", native_overlap="NO", overlaps_with=["Some Other Tool"]))
        self.assertEqual((v["stack_overlap"]["level"], v["score_parts"]["overlap"]), (NEW, 0.0))


class Keep(unittest.TestCase):
    def test_owned_use_with_nothing_new_becomes_keep(self):
        v = ev(cand("Owned Feature", owned="YES", recommendation="USE", improvement_opportunity="NO",
                    evidence_quality="STRONG"))
        self.assertEqual(v["verdict"], "KEEP")
        self.assertIn("USE -> KEEP", v["guard"])
        v = ev(cand("Owned Feature", owned="YES", recommendation="USE", evidence_quality="STRONG"))
        self.assertEqual(v["verdict"], "KEEP", "USE of an owned item with improvement UNKNOWN is KEEP")

    def test_owned_with_real_improvement_keeps_its_verdict(self):
        v = ev(cand("Owned Feature", owned="YES", recommendation="TEST", improvement_opportunity="YES",
                    evidence_quality="MODERATE"))
        self.assertEqual(v["verdict"], "TEST")

    def test_derived_keep_and_skill_keep(self):
        self.assertEqual(ev(cand("Example Chat Pro", evidence_quality="STRONG"))["verdict"], "KEEP")
        self.assertEqual(ev(cand("Owned", owned="YES", recommendation="KEEP"))["verdict"], "KEEP")
        v = ev(cand("Not Owned", recommendation="KEEP", improvement_opportunity="YES", evidence_quality="MODERATE"))
        self.assertEqual(v["verdict"], "TEST", "KEEP needs an owned item; verdict is derived instead")
        self.assertIn("KEEP needs an owned item", v["guard"])

    def test_keep_is_not_capped_by_evidence_but_archived_is_ignore(self):
        bare = normalize_candidate({"name": "Example Chat Pro", "category": "models"}, CATS)[0]
        self.assertEqual(ev(bare)["verdict"], "KEEP")
        self.assertEqual(ev(cand("Example Chat Pro", status="ARCHIVED", recommendation="KEEP"))["verdict"], "IGNORE")

    def test_keep_never_heads_a_lane(self):
        owned = cand("Example Chat Pro", evidence_quality="STRONG", status="ACTIVE", recommendation="USE",
                     improvement_opportunity="NO", popularity={"users": 10 ** 8})
        weak = cand("Small Thing", evidence_quality="WEAK", recommendation="WATCH")
        self.assertEqual([v["verdict"] for v in rank([owned, weak], PROF, CATS, TODAY)], ["WATCH", "KEEP"])


class JobFit(unittest.TestCase):
    def test_per_job_relevance_and_matched_jobs(self):
        c = cand("Brief Writer", capability="cited research briefs", job="write research briefs with cited sources")
        fit, matched = per_job_fit(c, PROF)
        # job 1 terms: resear quest write cited brief verifi source (7); hits: brief cited resear source write (5)
        self.assertEqual([m["job"] for m in matched], [PROF["jobs"][0]])
        self.assertEqual(matched[0]["terms"], ["brief", "cited", "resear", "source", "write"])
        self.assertEqual(matched[0]["relevance"], round(5 / 7, 3))
        self.assertEqual(fit, 1.0)
        self.assertEqual(ev(c)["score_parts"]["job_fit"], JOB_FIT_POINTS)

    def test_single_shared_word_is_not_a_match(self):
        fit, matched = per_job_fit(cand("Notes", job="clear notes"), PROF)
        # job 2 terms: turn rough meetin note clear docume (6); hits: clear note -> relevance 0.333 -> fit 0.333/0.5
        self.assertEqual((fit, matched[0]["terms"]), (0.666, ["clear", "note"]))
        fit, matched = per_job_fit(cand("Solo", job="research everything"), PROF)
        self.assertEqual((fit, matched), (0.0, []), "one shared term is noise")

    def test_many_jobs_do_not_saturate(self):
        jobs = "\n".join(f"- job {i}: manage research writing coding presentations documents automation agents tasks "
                         f"email calendar notes topic{i}" for i in range(12))
        prof = P.parse(f"## Jobs\n{jobs}\n")
        fit, matched = per_job_fit(cand("Generic", job="research agent"), prof)
        self.assertLess(fit, 0.5, "a long profile must not give a generic candidate a full fit")
        self.assertEqual(len(matched), 12)

    def test_first_real_scan_no_longer_saturates(self):
        led, prof = rerank_ledger()
        views = rank(led["entries"].values(), prof, CATS, date(2026, 10, 30), include_ignored=True)
        n_max = sum(1 for v in views if v["job_fit"] == 1.0)
        self.assertEqual(len(views), 58)
        self.assertLess(n_max, 12, f"{n_max} of 58 at maximum job_fit (0.1.0: 46 of 58)")
        self.assertGreater(len({v["job_fit"] for v in views}), 8, "job_fit discriminates")


def rerank_ledger():
    led = L.empty()
    for r in json.loads((RERANK / "scan-2026-10-30-annotated.json").read_text(encoding="utf-8"))["candidates"]:
        L.upsert(led, normalize_candidate(r, CATS, "2026-10-30")[0], "2026-10-30")
    return led, P.load(FIRST / "profile.md")


class CapabilityRanking(unittest.TestCase):
    def setUp(self):
        self.entries = [
            # uncovered, relevant, credible
            cand("Brief Checker", capability="Cited research briefs", job="check cited sources in research briefs",
                 recommendation="TEST", improvement_opportunity="YES", evidence_quality="MODERATE",
                 benchmark_needed="YES", native_overlap="NO"),
            cand("Brief Bot", capability="cited research, briefs", job="write research briefs",
                 recommendation="WATCH", evidence_quality="WEAK", benchmark_needed="NO"),
            # relevant but already covered by an owned item
            cand("Example Chat Pro", capability="note to document drafting", job="turn rough notes into clear documents",
                 recommendation="USE", improvement_opportunity="NO", evidence_quality="STRONG"),
            cand("Notes Polisher", capability="note to document drafting", job="turn rough notes into documents",
                 recommendation="TEST", improvement_opportunity="UNKNOWN", evidence_quality="MODERATE",
                 benchmark_needed="NO", native_overlap="YES", overlaps_with=["Example Chat Pro"]),
            # irrelevant and ignored
            cand("Old Thing", capability="legacy sync", recommendation="IGNORE", evidence_quality="WEAK"),
            cand("Loose Tool"),
        ]
        self.groups, self.unassigned = capability_opportunities(self.entries, PROF, CATS, TODAY)
        self.by = {g["key"]: g for g in self.groups}

    def test_grouping(self):
        self.assertEqual(len(self.groups), 3)
        g = self.by["cited research briefs"]
        self.assertEqual((g["candidate_count"], g["members"]), (2, ["Brief Bot", "Brief Checker"]))
        self.assertEqual([v["name"] for v in self.unassigned], ["Loose Tool"])

    def test_group_fields(self):
        g = self.by["cited research briefs"]
        for k in ("capability", "candidate_count", "best_candidates", "coverage", "verdicts", "strongest_verdict",
                  "benchmark_needed", "evidence_strength", "opportunity_score", "reason", "matched_jobs"):
            self.assertIn(k, g)
        self.assertEqual(g["best_candidates"][0]["name"], "Brief Checker")
        self.assertEqual((g["coverage"], g["strongest_verdict"], g["evidence_strength"]), ("NONE", "TEST", "MODERATE"))
        self.assertEqual(g["verdicts"], {"TEST": 1, "WATCH": 1})
        self.assertEqual(g["matched_jobs"], [PROF["jobs"][0]])

    def test_ranking_and_covered_capability_ranks_lower(self):
        self.assertEqual([g["key"] for g in self.groups],
                         ["cited research briefs", "note to document drafting", "legacy sync"])
        covered = self.by["note to document drafting"]
        self.assertEqual((covered["coverage"], covered["owned"]), ("COVERED", ["Example Chat Pro"]))
        self.assertEqual(covered["factors"]["gap"], 0.0)
        self.assertLess(covered["opportunity_score"], self.by["cited research briefs"]["opportunity_score"])
        self.assertEqual(self.by["legacy sync"]["factors"]["weak_share"], 1.0)

    def test_score_is_the_documented_formula(self):
        g = self.by["cited research briefs"]
        f = g["factors"]
        expected = 3.0 * f["relevance"] + 2.5 * f["gap"] + 2.0 * f["credibility"] + 1.5 * f["evidence"] \
            + 1.0 * f["improvement"] - 1.0 * f["weak_share"]
        self.assertAlmostEqual(g["opportunity_score"], round(expected, 2))
        self.assertEqual((f["gap"], f["credibility"], f["evidence"], f["improvement"]), (1.0, 0.75, 0.75, 1.0))

    def test_benchmark_aggregation(self):
        self.assertEqual(self.by["cited research briefs"]["benchmark_needed"], "YES", "any USE/TEST needing one")
        self.assertEqual(self.by["note to document drafting"]["benchmark_needed"], "NO")
        self.assertEqual(self.by["legacy sync"]["benchmark_needed"], UNKNOWN, "no USE/TEST candidate")

    def test_deterministic(self):
        again, _ = capability_opportunities(list(reversed(self.entries)), PROF, CATS, TODAY)
        self.assertEqual(again, self.groups)


class IdempotentIngest(unittest.TestCase):
    def test_same_scan_twice_changes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            ws = str(Path(d) / "radar")
            run("init", "--dir", ws, "--example")
            scan = str(FIX / "scan_basic.json")
            run("ingest", "--dir", ws, scan, "--as-of", "2026-01-15")
            ledger_path = Path(ws) / "ledger.json"
            first = ledger_path.read_bytes()
            ranked = run("rank", "--dir", ws, "--json", "--as-of", "2026-01-15")[1]
            code, out = run("ingest", "--dir", ws, scan, "--as-of", "2026-01-15")
            self.assertEqual(code, 0)
            self.assertIn("skipped", out)
            # same content under another name or formatting is the same scan
            copy = Path(d) / "renamed.json"
            copy.write_text(json.dumps(json.loads(Path(scan).read_text(encoding="utf-8"))), encoding="utf-8")
            self.assertIn("skipped", run("ingest", "--dir", ws, str(copy), "--as-of", "2026-01-15")[1])
            self.assertEqual(ledger_path.read_bytes(), first, "no duplicate candidates, history or seen counts")
            self.assertEqual(run("rank", "--dir", ws, "--json", "--as-of", "2026-01-15")[1], ranked)
            led = L.load(ledger_path)
            self.assertEqual(len(led["scans"]), 1)
            self.assertTrue(all(len(e["verdict_history"]) == 1 for e in led["entries"].values()))

    def test_changed_scan_is_still_ingested(self):
        with tempfile.TemporaryDirectory() as d:
            ws = str(Path(d) / "radar")
            run("init", "--dir", ws, "--example")
            data = json.loads((FIX / "scan_basic.json").read_text(encoding="utf-8"))
            run("ingest", "--dir", ws, str(FIX / "scan_basic.json"), "--as-of", "2026-01-15")
            data["scan"]["date"] = "2026-02-01"
            newer = Path(d) / "scan-2026-02-01.json"
            newer.write_text(json.dumps(data), encoding="utf-8")
            self.assertIn("0 new, 8 merged", run("ingest", "--dir", ws, str(newer), "--as-of", "2026-02-01")[1])

    def test_matched_jobs_persist_in_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            ws = str(Path(d) / "radar")
            run("init", "--dir", ws)
            (Path(ws) / "profile.md").write_text((FIX / "profile.md").read_text(encoding="utf-8"), encoding="utf-8")
            run("ingest", "--dir", ws, str(FIX / "scan_basic.json"), "--as-of", "2026-01-15")
            e = L.load(Path(ws) / "ledger.json")["entries"]["skills/doc-writer"]
            self.assertEqual(e["job_fit"], 1.0)
            self.assertEqual([m["job"] for m in e["matched_jobs"]], ["turn rough notes into clear documents"])


class Reports(unittest.TestCase):
    def test_opportunities_command_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            ws = str(Path(d) / "radar")
            run("init", "--dir", ws)
            (Path(ws) / "profile.md").write_text((FIX / "profile.md").read_text(encoding="utf-8"), encoding="utf-8")
            run("ingest", "--dir", ws, str(FIX / "scan_basic.json"), "--as-of", "2026-01-15")
            code, out = run("opportunities", "--dir", ws, "--as-of", "2026-01-15")
            self.assertEqual(code, 0)
            self.assertIn("TOP 10 CAPABILITY OPPORTUNITIES", out)
            md = (Path(ws) / "reports" / "opportunities-2026-01-15.md").read_text(encoding="utf-8")
            self.assertIn("## TOP CAPABILITY OPPORTUNITIES", md)
            self.assertIn("web research with citations", md.lower())
            self.assertIn("Without a capability", md)
            data = json.loads(run("opportunities", "--dir", ws, "--json", "--as-of", "2026-01-15")[1])
            caps = {g["key"]: g for g in data["capabilities"]}
            self.assertEqual(caps["web research with citations"]["candidate_count"], 2, "case-insensitive grouping")
            self.assertEqual(caps["web research with citations"]["coverage"], "COVERED")
            self.assertIn("Mystery Tool", data["unassigned"])
            ranked = json.loads(run("rank", "--dir", ws, "--json", "--as-of", "2026-01-15")[1])
            self.assertIn("matched_jobs", ranked["oss"][0])

    def test_empty_capability_report(self):
        md = R.build_capabilities(L.empty(), PROF, CATS, TODAY)
        self.assertIn("No capability groups yet", md)


def sha(p):
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()  # a CRLF checkout is not a change


class Artifacts(unittest.TestCase):
    """The 0.1.0 evidence is history: the 0.1.1 rerank lives in its own folder and is reproducible."""

    HISTORICAL = {
        "examples/first-real-scan-2026-10-30/README.md":
            "52bb3938e5bbab001c8ce5ae7c894d0b32ec7fa1b2c29baea21928e4e4be7d11",
        "examples/first-real-scan-2026-10-30/clean-install-validation.md":
            "318f31b575a3397dd7b04040fb64ee19312446b1bdbc1070036bc25259ef0fbb",
        "examples/first-real-scan-2026-10-30/ledger-2026-10-30.json":
            "e900f7fb67b4b6c7ba9fae6a2cc4bb2c8e9a1278b7b7dc1af7831264dcd564f9",
        "examples/first-real-scan-2026-10-30/profile.md":
            "f4ad00bd2e54b68b72b1d6cccdc73ca0f93b10787147052b92d3d14f9b8e03bb",
        "examples/first-real-scan-2026-10-30/radar-evaluation.md":
            "03d60b32ecf4fc8abaf895a95568590940aaf938ba73e72ae086187f8d7ec7ae",
        "examples/first-real-scan-2026-10-30/report-2026-10-30.md":
            "f36641a741359888e6ed87d4aebfe77e6cfea6a40c1d2867ac0acdb332005d89",
        "examples/first-real-scan-2026-10-30/reverify-2026-10-30.txt":
            "dad7daf1b6f75f20ef6ae6e5eb8592cbb120eea83b61c7348512df41ab3d585f",
        "examples/first-real-scan-2026-10-30/scan-2026-10-30.json":
            "a57fca3786de48bf1b949bb380e381e3c615737ec240c8502445adb68328afaf",
        "examples/first-real-scan-2026-10-30/scan-plan-2026-10-30.json":
            "ddc91ea7e84170e3437cccdd70eb7e4251921ef6b09c0e81bc82c754c3c2a4f6",
        "examples/first-real-scan-2026-10-30/top-opportunities.md":
            "d3a62592e25506d6845f95aa0d84123f61f9b8d5791fc54168bcbbb0a2ded566",
        "examples/ledger-2026-10-30.json":
            "c4cbd8b790da39df3271dfa32218456de066a968379da6008ddea9a92fe5d009",
        "examples/report-2026-10-30.md":
            "e32bdcabcc71d5af94edd6045f83f9e0773a852ad88051d5be6659f0c663ff88",
        "examples/reverify-example.txt":
            "27eaba5fe4b3c273ba7a5dc1984d47ccee86aa9fc2ff52af70e5e3f3d46dfe8a",
        "examples/scan-2026-10-30.json":
            "42a053878fdb1f8030cbe35fdee2fb45bc1203e29d9ce0d71cdd9bc55272ef73",
        "examples/scan-plan-2026-10-30.json":
            "fe4e9f1a28c4a3d261872b15e62266427e861d699726a017fb890806f363376a",
    }

    def test_historical_0_1_0_artifacts_unchanged(self):
        changed = [rel for rel, digest in self.HISTORICAL.items() if sha(ROOT / rel) != digest]
        self.assertEqual(changed, [])

    def test_annotated_scan_only_adds_capability_and_owned(self):
        orig = json.loads((FIRST / "scan-2026-10-30.json").read_text(encoding="utf-8"))
        ann = json.loads((RERANK / "scan-2026-10-30-annotated.json").read_text(encoding="utf-8"))
        self.assertEqual({k: v for k, v in ann["scan"].items() if k != "annotations"}, orig["scan"])
        self.assertEqual(len(ann["candidates"]), len(orig["candidates"]))
        for a, o in zip(ann["candidates"], orig["candidates"]):
            self.assertEqual({k: v for k, v in a.items() if k not in ("capability", "owned")}, o)
            self.assertNotIn("capability", o)
            self.assertIn(a.get("owned"), (None, "YES"))

    def test_rerank_artifacts_are_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            ws = str(Path(d) / "radar")
            run("init", "--dir", ws)
            (Path(ws) / "profile.md").write_bytes((FIRST / "profile.md").read_bytes())
            run("ingest", "--dir", ws, str(RERANK / "scan-2026-10-30-annotated.json"), "--as-of", "2026-10-30")
            run("dedupe", "--dir", ws)
            run("report", "--dir", ws, "--top", "10", "--as-of", "2026-10-30")
            run("opportunities", "--dir", ws, "--top", "10", "--as-of", "2026-10-30")
            out = Path(ws)
            self.assertEqual((out / "ledger.json").read_text(encoding="utf-8"),
                             (RERANK / "ledger-2026-10-30.json").read_text(encoding="utf-8"))
            self.assertEqual((out / "reports/radar-2026-10-30.md").read_text(encoding="utf-8"),
                             (RERANK / "report-2026-10-30.md").read_text(encoding="utf-8"))
            self.assertEqual((out / "reports/opportunities-2026-10-30.md").read_text(encoding="utf-8"),
                             (RERANK / "opportunities-2026-10-30.md").read_text(encoding="utf-8"))

    def test_capabilities_are_data_not_code(self):
        ann = json.loads((RERANK / "scan-2026-10-30-annotated.json").read_text(encoding="utf-8"))
        caps = {c["capability"].lower() for c in ann["candidates"]}
        code = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "capradar").glob("*.py")).lower()
        self.assertEqual(sorted(c for c in caps if c in code), [])


if __name__ == "__main__":
    unittest.main()
