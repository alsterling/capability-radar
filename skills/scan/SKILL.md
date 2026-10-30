---
name: scan
description: Capability Radar scan. Use when the user asks what AI tools, Skills, plugins, connectors, MCP servers, agents, open-source repos, model features, research/search tools or automation tools are worth adopting, testing or watching for their jobs, or asks to run, refresh or re-verify the capability radar. Arguments - "--all" (default), a lane name such as "mcp" or "skills", and "--top N".
---

# Capability Radar: scan

You are the discovery and reasoning layer. The `capradar` CLI is the deterministic layer: it plans, dedupes, ranks, stores and reports. You never install, enable, buy or authorize anything. "Nothing worth changing" is a valid result.

## 0. Run the CLI

Use `python -m capradar <command>`. If Python cannot find `capradar`, prefix the command with `PYTHONPATH=<plugin root>` (the plugin root is the folder two levels above this file), or run `pip install -e <plugin root>` once. The workspace defaults to `./radar` (override with `--dir` or `CAPRADAR_HOME`).

## 1. Plan

1. If `radar/ledger.json` does not exist, run `python -m capradar init` (or `init --example` for the synthetic demo profile) and ask the user to fill `radar/profile.md`: jobs, current stack, constraints. If they decline, continue with what is there and say so.
2. Run `python -m capradar scan --all --top 10`, or `scan --category <lane>` for a lane-specific scan. Read the plan it writes (`radar/inbox/scan-plan-<date>.json`): lanes, profile, entries already in the ledger, entries due for re-verification, and the candidate contract.

## 2. Check the existing stack first

For each lane, before searching the market, list what the user already has (profile current stack) and what their platforms do natively (official docs/changelog of each owned platform). A candidate that only duplicates something owned or native gets `native_overlap` YES or PARTIAL and `overlaps_with`, and usually `improvement_opportunity` NO.

## 3. Discover, per lane

Use your web search and fetch tools. Use several source types per lane, not one:

| Query family | Examples |
|---|---|
| Official registry / marketplace | plugin or connector directory, MCP registry, Skill marketplace, model release notes |
| Vendor docs and changelogs (last 90 days) | "what's new", release notes, pricing pages |
| Source repositories | GitHub search by topic, sorted by recent activity, not only stars |
| Curated lists | "awesome-*" lists (discovery only: a list is never evidence that a tool works) |
| Independent evaluation | benchmarks, evals, reproducible comparisons |
| Practitioner reports | reviews, issue trackers, forums (label as practitioner, tier 3) |

Rules (learned from earlier recall/support failures):
- **Recall and support are separate gates.** Finding a tool is not evidence it works. Every material claim (what it does, status, cost, permissions) needs a source URL you actually opened.
- **Saturation:** stop a lane when two consecutive query families add no new relevant candidate, or after about 8 queries. Note in the scan file whether the lane saturated or hit the limit.
- **Popularity is not evidence.** Record stars/downloads/installs in `popularity`; judge `evidence_quality` only from what shows the tool improves a job:
  - STRONG: independent measured results (benchmark, eval, reproducible comparison), or vendor results reproduced by others;
  - MODERATE: official docs that demonstrate the capability, or a vendor's own benchmark with method disclosed, or credible independent reports;
  - WEAK: README / marketing claims only;
  - ANECDOTAL: social posts, single anecdotes;
  - UNKNOWN: could not tell.
- **Freshness:** record `status` (ACTIVE, MAINTAINED, PREVIEW, STALE, ARCHIVED, DEPRECATED) and `last_activity` (latest release or commit date) from the source, not from memory.
- **Dedupe while you go:** name the canonical project; list wrappers, forks and renamed copies in `aliases`, or set `duplicate_of`. Give each candidate its own `repo` URL when it has one.
- **Exact job:** `job` names the concrete capability it improves ("search the web with citations from inside the coding agent"), not a category.
- **Capability:** `capability` names the job it provides, separate from the product ("context and token efficiency" for a context-compression tool). Use the same wording for every candidate of the same capability, including owned features, so the CLI can group them. Leave it out if unsure; the CLI never invents one.
- **Owned:** set `owned: YES` when the user already has it (a current-stack item, or a feature included in one).
- **Never invent.** Use `UNKNOWN` for anything you could not verify. Do not fill cost, privacy or permissions from memory.

## 4. Judge

For each candidate set `recommendation` (USE / TEST / WATCH / KEEP / IGNORE), `reason`, `benchmark_needed` (YES when the gain must be proven on the user's own job first), `improvement_opportunity` (YES / NO / UNKNOWN for this profile) and, if useful, `reverify_trigger`.
- USE only with strong evidence, an official source, no benchmark needed and a clear gain. The CLI caps verdicts the evidence does not support, and shows the cap in the report.
- TEST when the gain is plausible and worth a short trial on a real job.
- WATCH when it is promising but immature, unproven or not yet relevant.
- KEEP when it is already owned and still adequate: nothing new to adopt. (The CLI also turns an owned USE with improvement NO into KEEP.)
- IGNORE when it is archived, duplicates what the user has, or does not fit.

## 5. Write, ingest, report

1. Write `radar/inbox/scan-<date>.json`: `{"scan": {"date": ..., "lanes": [...], "queries": [...], "saturation": {...}}, "candidates": [...]}` using the contract in the scan plan.
2. `python -m capradar ingest radar/inbox/scan-<date>.json` (fix and re-ingest any REJECTED lines).
3. `python -m capradar dedupe`
4. `python -m capradar report --top 10` → `radar/reports/radar-<date>.md`
5. `python -m capradar opportunities --top 10` → `radar/reports/opportunities-<date>.md` (capability-level ranking)
6. `python -m capradar reverify`

## 6. Answer the user

Give the TOP CAPABILITY OPPORTUNITIES from `capradar opportunities` (or "nothing worth changing"), the best candidates for each, the report path, any guard caps, and what is due for re-verification. Do not install anything; for a TEST item, suggest the smallest real-job trial.
