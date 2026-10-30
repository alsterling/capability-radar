import json
import unittest
from pathlib import Path

from capradar.core import (UNKNOWN, candidate_keys, load_categories, name_key, normalize_candidate, normalize_url,
                           repo_key, resolve_category)

FIX = Path(__file__).parent / "fixtures"
CATS = load_categories()


def raw(name):
    return next(c for c in json.loads((FIX / "scan_basic.json").read_text(encoding="utf-8"))["candidates"] if c["name"] == name)


class Categories(unittest.TestCase):
    def test_eight_default_lanes(self):
        self.assertEqual([c["id"] for c in CATS],
                         ["skills", "plugins_connectors", "mcp", "agents", "oss", "models", "research_search", "automation"])

    def test_aliases_and_labels_resolve(self):
        self.assertEqual(resolve_category("MCP servers", CATS), "mcp")
        self.assertEqual(resolve_category("Plugins / Connectors", CATS), "plugins_connectors")
        self.assertEqual(resolve_category("skill", CATS), "skills")

    def test_unknown_lane_rejected(self):
        with self.assertRaises(ValueError):
            resolve_category("hardware", CATS)

    def test_new_lane_needs_no_code(self):
        cats = load_categories({"categories": CATS + [{"id": "hardware", "label": "Hardware", "freshness_days": 90}]})
        c, _ = normalize_candidate({"name": "Gadget", "category": "hardware"}, cats, "2026-01-01")
        self.assertEqual(c["category"], "hardware")


class Normalize(unittest.TestCase):
    def test_enums_urls_and_tiers(self):
        c, warns = normalize_candidate(raw("Acme Search MCP Server"), CATS, "2026-01-10")
        self.assertEqual((c["status"], c["evidence_quality"], c["native_overlap"]), ("ACTIVE", "MODERATE", "PARTIAL"))
        self.assertEqual(c["sources"][0]["url"], "https://github.com/acme/acme-search-mcp")
        self.assertEqual(c["sources"][1]["tier"], "TIER1_OFFICIAL")
        self.assertEqual(c["source_tier"], "TIER1_OFFICIAL")
        self.assertEqual(c["repo"], "github.com/acme/acme-search-mcp")
        self.assertEqual(warns, [])

    def test_unknown_fields_stay_unknown(self):
        c, _ = normalize_candidate(raw("Mystery Tool"), CATS, "2026-01-10")
        for f in ("job", "description", "cost", "privacy", "permissions", "version", "status", "evidence_quality",
                  "improvement_opportunity", "benchmark_needed", "last_verified", "reverify_after"):
            self.assertEqual(c[f], UNKNOWN, f)
        self.assertIsNone(c["recommendation"])
        self.assertEqual(c["derived"], [], "no source -> last_verified is not invented")

    def test_bad_enum_becomes_unknown_with_warning(self):
        c, warns = normalize_candidate({"name": "X", "category": "mcp", "evidence_quality": "amazing"}, CATS)
        self.assertEqual(c["evidence_quality"], UNKNOWN)
        self.assertTrue(any("evidence_quality" in w for w in warns))

    def test_policy_derived_dates_are_marked(self):
        c, _ = normalize_candidate(raw("Acme Search MCP Server"), CATS, "2026-01-10")
        self.assertEqual((c["last_verified"], c["reverify_after"]), ("2026-01-10", "2026-02-24"))
        self.assertEqual(c["derived"], ["last_verified=scan_date", "reverify_after=last_verified+45d"])

    def test_missing_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_candidate({"name": "", "category": "mcp"}, CATS)

    def test_url_normalization(self):
        self.assertEqual(normalize_url("WWW.Example.com/a/?utm_medium=x&q=1#frag"), "https://example.com/a?q=1")
        self.assertEqual(repo_key("https://github.com/Owner/Repo.git/tree/main"), "github.com/owner/repo")
        self.assertIsNone(repo_key("https://gitlab.com/owner/repo"))


class Keys(unittest.TestCase):
    def test_name_key_drops_generic_words(self):
        self.assertEqual(name_key("Acme Search MCP Server"), name_key("acme-search mcp"))
        self.assertEqual(name_key("The Official GitHub MCP Server (preview)"), "github")
        self.assertEqual(name_key("MCP"), "mcp", "all-generic names keep their tokens")

    def test_shared_list_page_is_not_identity(self):
        a, _ = normalize_candidate({"name": "Tool A", "category": "mcp", "sources": [
            {"url": "https://github.com/someone/awesome-list", "type": "other"}]}, CATS)
        b, _ = normalize_candidate({"name": "Tool B", "category": "mcp", "sources": [
            {"url": "https://github.com/someone/awesome-list", "type": "other"}]}, CATS)
        self.assertFalse(candidate_keys(a) & candidate_keys(b))


if __name__ == "__main__":
    unittest.main()
