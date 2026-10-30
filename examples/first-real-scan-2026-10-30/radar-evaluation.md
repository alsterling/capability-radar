# Capability Radar 0.1.0 — evaluation from the first real scan

Scan: 2026-10-30, 8 lanes, 59 candidate records → 58 ledger entries. Verdicts: 5 USE, 26 TEST, 19 WATCH, 8 IGNORE. No code was changed for this run.

## Questions

| Question | Answer |
|---|---|
| Did all 8 lanes work? | **Yes.** Every lane got 6–9 candidates; plan, ingest, rank, report and reverify handled all 8 with no rejected records and no warnings. |
| Were obvious duplicates handled? | **Yes, within a lane.** `serena-slim` (a fork, marked `duplicate_of: Serena`) merged into Serena with its alias and sources kept. The Skill step "dedupe while you go" also kept forks out (RTK mirrors, Caveman copies). **Cross-lane duplicates are not detected by design** (e.g. a tool that is both an MCP server and an automation platform); the Skill has to pick one lane. |
| Did current-stack-first logic work? | **In the verdicts, yes; in the scores, it works against itself.** The Skill's stack-first step produced the right calls: GitHub MCP Server, Copilot coding agent, Jules and OpenCode → IGNORE as duplicates of owned tools; owned capabilities with nothing to change → USE with `improvement: NO`, kept out of top opportunities. But scoring stacks two penalties (native overlap −1.5, stack overlap −1.0) on *owned features that are themselves the opportunity*: 10 such entries (e.g. Claude scheduled tasks scores 5.0 vs n8n 7.4). |
| Did it avoid padding? | **Mostly.** No lane reached 10; lanes stopped at 6–9 with saturation recorded. Some entries exist to show coverage rather than to recommend (owned USE items, IGNORE duplicates); they are labeled as such. |
| Are recommendations understandable? | **Yes at the entry level** (job, reason, evidence notes, caps). **Weaker at the lane level:** tables sort by verdict before score, so an owned USE item with nothing to change (GPT-6 family, score 4.5) heads the Models lane above a real opportunity (Claude 5.5 routing, 9.25). The USE verdict means both "adopt now" and "already have, keep". |
| Does the ledger preserve candidates correctly? | **Yes.** 58 entries with aliases, sources (tier, type, read method in `note`), cost/privacy/permissions, verdict history, reverify dates and triggers. Re-ingest in a new process kept entries stable and merged sources by URL. |
| Does reverify work? | **Yes.** As of scan date: 0 stale, 0 due, 28 trigger watches. As of 2026-12-20: 32 stale, 32 due, 4 lanes needing a fresh scan (lanes with 30–45 day windows). See `reverify-2026-10-30.txt`. |
| Did scoring produce an obviously bad recommendation? | **No bad verdict.** Verdicts come from the Skill and are capped by evidence; no cap fired, because the Skill already proposed verdicts within the evidence. **Ordering has two weaknesses:** (1) `job_fit` saturates (46 of 58 at the 1.5 cap; a 10-job profile yields 99 keywords), so it barely discriminates; (2) evidence quality dominates, so a well-documented but niche item (Elicit, WATCH, 8.75) outranks a more relevant TEST (Exa, 7.75), and the CLI's top opportunity is SkillsBench, an evaluation tool, rather than a primary-job capability. |
| Anything blocking normal personal use? | **No.** |
| Anything blocking a future public alpha? | **One repository setting:** the GitHub default branch is `claude/v0.1.0-public-alpha`, not `main`. Fix that before the repo goes public. Otherwise nothing blocking; see follow-ups. |

## What the CLI could not express

This task asked for top opportunities as **capabilities** ("context/token efficiency — X is one candidate"). The CLI ranks **products** only; there is no field for the capability/job an entry belongs to, so the capability-level ranking in [`top-opportunities.md`](top-opportunities.md) was written by hand from the ledger. This is the largest gap between what the radar produced and what a reviewer needed.

## Follow-up (non-blocking, parked)

1. Set the GitHub default branch to `main` (repository setting; required before public alpha).
2. Add a `capability` (job) field and group top opportunities by it in the report.
3. Separate "already owned, keep" from "adopt now" (an `OWNED` / `KEEP` marker or verdict), and don't let owned items head lane tables by verdict alone.
4. Don't apply both native-overlap and stack-overlap penalties when the candidate *is* the owned native feature and `improvement_opportunity` is YES.
5. Make `job_fit` discriminate: match per job (best-matching job), not against the union of all job keywords.
6. Skill: allow and document a source read method (`fetched` / `search-read`) for sessions where direct fetch is blocked; name a fallback for `last_activity` when no repository API is available (commit pages).
7. README: say "use a virtual environment" for `pip install -e .`.
8. Make re-ingesting the same scan file idempotent (today it increments `seen_count` and adds a scan record).
9. Note in the Skill that cross-lane duplicates are not merged, so each tool must be filed in one lane.
10. `name_key` drops parenthesized text, so two products that differ only in a parenthetical would merge. No false merge happened in this run.
11. Optional: a `--capability` or `--job` filter on `rank`/`report`.

## Evidence-capture limits of this run

- Direct fetch was blocked for most hosts (including help.openai.com); those sources were read through the search tool and labeled `search-read`. ChatGPT/Codex facts therefore rest on the search tool's reading of official pages.
- GitHub's REST API was unavailable; star counts come from repo pages and `last_activity` from commit pages. Several repos show `UNKNOWN` where the page gave no date.
- One assistant session, standard web search. A sample per lane, not a census.
