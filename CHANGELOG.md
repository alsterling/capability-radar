# Changelog

## 0.1.1 — opportunity ranking hardening

Fixes from the first real scan; no new capability.

- `capability` field: what a candidate does, separate from the product name. Missing stays `UNKNOWN`; never inferred.
- `owned` field and **KEEP** verdict: an owned item with nothing new to adopt is KEEP, not USE, and no longer heads lane tables.
- Current-stack relation replaces IN_STACK/OVERLAP: `ALREADY_OWNED_SAME_CAPABILITY`, `COMPLEMENTS_CURRENT_STACK`, `DUPLICATES_CURRENT_STACK`, `NEW_CAPABILITY`. One overlap penalty at most, only for duplicates; owned and complementary items are not penalized.
- Per-job `job_fit` (best single job, at least 2 shared terms, normalized 0–1); matched jobs shown in reports and stored in the ledger. On the first real scan, maximum job fit drops from 46 of 58 candidates to 8.
- `capradar opportunities`: capability-level ranking (TOP CAPABILITY OPPORTUNITIES) with coverage, best candidates, verdicts, benchmark need, evidence strength and a documented 0–10 score; also summarized in `report`.
- Idempotent ingest: identical scan content is skipped (fingerprint stored per scan).
- README: virtual-environment setup.
- First real scan reranked under 0.1.1 in `examples/first-real-scan-2026-10-30-rerank-v0.1.1/`; 0.1.0 artifacts unchanged.

## 0.1.0 — public alpha candidate

- Skill `scan` (`/capability-radar:scan`) for discovery and judgment.
- Stdlib CLI: `init`, `scan` (plan), `ingest`, `dedupe`, `rank`, `report`, `reverify`.
- 8 default lanes as data (`capradar/data/categories.json`); add lanes without code changes.
- JSON ledger with aliases, verdict history, evidence, cost/privacy/permissions, reverify dates.
- Evidence-first ranking with popularity capped; USE/TEST/WATCH/IGNORE with evidence caps.
- Synthetic example profile and one dogfood report.
