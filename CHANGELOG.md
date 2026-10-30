# Changelog

## 0.1.0 — public alpha candidate

- Skill `scan` (`/capability-radar:scan`) for discovery and judgment.
- Stdlib CLI: `init`, `scan` (plan), `ingest`, `dedupe`, `rank`, `report`, `reverify`.
- 8 default lanes as data (`capradar/data/categories.json`); add lanes without code changes.
- JSON ledger with aliases, verdict history, evidence, cost/privacy/permissions, reverify dates.
- Evidence-first ranking with popularity capped; USE/TEST/WATCH/IGNORE with evidence caps.
- Synthetic example profile and one dogfood report.
