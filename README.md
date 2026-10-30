# Capability Radar

**Status: 0.1.1 public alpha. Not production-ready.**

An on-demand radar for AI capabilities: Skills, plugins/connectors, MCP servers, agents, open-source projects, model features, research/search tools and automation tools. It checks what you already have, searches current public sources, dedupes wrappers and forks, ranks by **evidence rather than popularity**, keeps a local ledger, and tells you what to re-verify.

**Why:** new Skills, plugins, MCP servers and agent tools appear every week, most are wrappers or forks of each other, and star counts say little about whether a tool improves your own work. Capability Radar answers "what is worth adopting, testing or watching for my jobs, given what I already have?" with sources, an evidence-capped verdict, and a date to check again.

**It never installs anything.** It recommends; you decide. "Nothing worth changing" is a valid result.

## How it works

| Layer | What | Where |
|---|---|---|
| Discovery and judgment | A Skill your assistant runs: checks your stack, searches several source types per lane, verifies, fills a candidate file | `skills/scan/SKILL.md` |
| Deterministic core | A stdlib Python CLI: plan, ingest, dedupe, rank, report, reverify. No network calls, no dependencies | `capradar/` |
| Memory | JSON ledger + Markdown profile and reports in a local workspace (`./radar`) | your disk |

## Install

**As a Claude Code plugin** (gives `/capability-radar:scan`):

```bash
claude plugin marketplace add alsterling/capability-radar
```

```bash
claude plugin install capability-radar@capability-radar
```

Start a new Claude Code session afterwards so the Skill loads. On Claude on the web, add `alsterling/capability-radar` as a plugin marketplace and enable `capability-radar` there. To install from a local clone instead, run `claude plugin marketplace add ./capability-radar` (the folder you cloned), then the same `install` command.

The plugin's Skill runs the bundled CLI with `python -m capradar`, so Python 3.10+ must be on the machine (no packages needed).

**CLI only** (Python 3.10+, no dependencies):

```bash
git clone https://github.com/alsterling/capability-radar && cd capability-radar
```

Use a virtual environment (recommended). macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Or skip the install and run `python -m capradar` from the repo folder.

## Use

In Claude Code:

```
/capability-radar:scan --all --top 10
/capability-radar:scan mcp
```

Deterministic CLI equivalents:

```bash
python -m capradar init --example      # workspace ./radar with a synthetic profile (omit --example for a blank one)
python -m capradar scan --all --top 10  # writes radar/inbox/scan-plan-<date>.json for the Skill
python -m capradar scan --category mcp  # one lane
python -m capradar ingest radar/inbox/scan-<date>.json
python -m capradar dedupe
python -m capradar rank --top 10 [--category skills] [--json]
python -m capradar report --top 10      # radar/reports/radar-<date>.md
python -m capradar opportunities --top 10 [--json]  # capability-level ranking: radar/reports/opportunities-<date>.md
python -m capradar reverify [--json] [--write-plan]
```

All commands take `--dir` (workspace; default `./radar` or `$CAPRADAR_HOME`) and `--as-of YYYY-MM-DD`.

## Profile

`radar/profile.md` is plain Markdown: `## Jobs` (one recurring job per bullet), `## Current stack` (`Name | lane | what it covers`), `## Constraints`. The radar uses it for fit and current-stack overlap. A synthetic example is in [`capradar/data/profile.example.md`](capradar/data/profile.example.md). Keep secrets and client names out of it.

## Lanes

Eight default lanes, defined as data in [`capradar/data/categories.json`](capradar/data/categories.json) (copied to `radar/config.json` on `init`): Skills · Plugins / Connectors · MCP · Agents / persistent workers · GitHub / OSS · Models / native features · Research / search tools · Automation / workflow tools. Add a lane by adding an entry to `config.json`; no code change.

## Candidate fields

Name, lane, **capability** (the job it provides, separate from the product name; candidates with the same capability are grouped; missing stays `UNKNOWN` and is never inferred), **owned** (`YES` when already in the user's stack), exact job, description, source URLs with tier (`TIER1_OFFICIAL` / `TIER2_ECOSYSTEM` / `TIER3_PRACTICAL`) and type, status/maintenance, last activity, version, popularity signals, evidence quality (`STRONG` / `MODERATE` / `WEAK` / `ANECDOTAL`), cost, privacy, permissions, native overlap, overlaps with, relation to a current tool, recommendation, reason, benchmark needed, improvement opportunity (`YES` / `NO` / `UNKNOWN`), last verified, reverify date/trigger, aliases. Anything not established is `UNKNOWN`. `capradar scan` writes the full contract into each scan plan.

## Verdicts and ranking

- **USE** adopt or start using now · **TEST** try on a real job first · **WATCH** not yet · **KEEP** already owned and adequate, nothing to adopt · **IGNORE** skip.
- The Skill proposes a verdict; the CLI **caps** it by evidence. No source caps a verdict at WATCH. WEAK, ANECDOTAL or UNKNOWN evidence, or a needed benchmark, caps it at TEST. ARCHIVED or DEPRECATED means IGNORE. Caps are shown in the report. An owned item with improvement `NO` (or a USE with improvement `UNKNOWN`) becomes **KEEP**; KEEP sorts below WATCH and is listed apart from the lane tables.
- Score = evidence + source tier + source diversity + maintenance + improvement + job fit + overlap − staleness + popularity. Popularity is capped at 0.75 points, below one evidence step, and never changes a verdict.
- **Current-stack relation** (one penalty at most): `ALREADY_OWNED_SAME_CAPABILITY` (name/alias is a stack item, or `owned: YES`) 0 · `COMPLEMENTS_CURRENT_STACK` (`current_tool` relation COMPLEMENTS) 0 · `DUPLICATES_CURRENT_STACK` (names an owned tool in `overlaps_with`/`current_tool`, or `native_overlap` YES/PARTIAL) −1.5 if native YES, −0.5 if PARTIAL, else −1.0 · `NEW_CAPABILITY` 0.
- **Job fit** (0–1, worth up to 1.5 points), per profile job: terms = words of 4+ letters, not stopwords, plural `s` dropped, first 6 letters. For each job, relevance = shared terms ÷ the job's terms, counted only when at least 2 terms are shared. `job_fit = min(1, best relevance ÷ 0.5)`. The best single job decides, so a long profile does not inflate it. Matched jobs are shown in the report and stored in the ledger.
- **Top capability opportunities** (`capradar opportunities`) group candidates by capability. Opportunity (0–10) = 3.0·relevance (best job fit) + 2.5·gap (coverage NONE 1.0, UNKNOWN 0.75, PARTIAL 0.6, COVERED 0 when an owned candidate is KEEP) + 2.0·credibility (best of USE 1.0, TEST 0.75, WATCH 0.25) + 1.5·evidence (best, STRONG = 1) + 1.0·improvement (YES 1, UNKNOWN 0.5) − 1.0·weak share (IGNORE or full duplicates). Candidates without a capability are listed, not grouped.
- **Top product opportunities** = improvement `YES`, verdict USE/TEST.

## Ledger and dedupe

`radar/ledger.json` keeps every candidate ever seen (with its job fit and matched jobs as of the last ingest): aliases, verdict history (prior verdict), sources, cost/privacy/permissions, version, last verified, reverify date/trigger, and scan history. Duplicates are merged within a lane by normalized name ("Acme MCP Server" = "acme-mcp"), aliases, `duplicate_of`, or the candidate's own repository URL. A shared list page never merges two tools. A newer verification wins; UNKNOWN never overwrites a known value; a weaker-tier record never overwrites a stronger one from the same day. Ingest is idempotent: a scan whose content was already ingested (same parsed JSON, under any file name) is skipped, so it cannot duplicate candidates, verdict history or seen counts.

## Reverify

`capradar reverify` lists stale entries (older than the lane's freshness window, or never verified), entries whose reverify date has passed, entries with a reverify trigger to check, and lanes needing a fresh scan. `--write-plan` also saves the list to `radar/inbox/reverify-plan-<date>.json`. Reverify never edits the ledger; entries are updated only when a new scan is ingested. There is no scheduler: run it when you like, or ask the Skill to refresh what it lists.

## Example

The first dogfood run (2026-10-30, synthetic profile, 8 lanes, 35 candidates, 1 merged duplicate, 34 ledger entries):
- [`examples/report-2026-10-30.md`](examples/report-2026-10-30.md): the report
- [`examples/scan-2026-10-30.json`](examples/scan-2026-10-30.json): the candidate file the Skill wrote, with queries and sources opened
- [`examples/ledger-2026-10-30.json`](examples/ledger-2026-10-30.json), [`examples/scan-plan-2026-10-30.json`](examples/scan-plan-2026-10-30.json), [`examples/reverify-example.txt`](examples/reverify-example.txt)

The first real-use scan and its 0.1.1 rerank (capability-level ranking, KEEP, new job fit): [`examples/first-real-scan-2026-10-30/`](examples/first-real-scan-2026-10-30/) and [`examples/first-real-scan-2026-10-30-rerank-v0.1.1/`](examples/first-real-scan-2026-10-30-rerank-v0.1.1/).

The examples are snapshots from one session. Facts in it will go stale; that is what `reverify` is for.

## Tests

```bash
python -m unittest discover -s tests
```

Stdlib only, no network. They cover ingest (including idempotent re-ingest), normalization, alias/dedupe, ranking, top-N, lane filtering, all five verdicts, unknown fields, current-stack relation, per-job job fit, capability grouping and ranking, ledger persistence, stale/reverify detection, report generation, and public-safety checks: no personal markers, no network code, no candidate or capability names hardcoded in code, historical example artifacts unchanged.

## Limitations

- **Discovery quality depends on the assistant running the Skill** and its search tools. One scan samples each lane; it is not a census.
- **Judgments are the Skill's** (evidence quality, improvement opportunity, capability, owned). The CLI only caps them and ranks consistently. Scores are heuristic, not calibrated.
- **Not measured on your jobs.** TEST means "worth a short trial", not "proven better". The radar has no benchmark harness yet.
- **Job fit is lexical.** It matches words of the profile's jobs, not meaning; constraints are not scored. Write jobs in plain words.
- **Dedupe is rule-based.** Renamed projects with no shared name, alias or repo are not caught; mark them with `duplicate_of`.
- **No scheduler, server or database**, by design.
- **Alpha.** Tested with Claude Code: plugin install from GitHub and from a local clone, and Skill loading in local and web sessions. Other assistants can follow `skills/scan/SKILL.md` by hand; that path is less tested.
- **Results go stale.** A verdict is a snapshot with a verification date; run `reverify` before acting on an old one.

## Privacy

See [PRIVACY.md](PRIVACY.md). Short version: the CLI makes no network calls and sends no telemetry; your workspace stays on your disk; nothing is installed or authorized for you.

## License

MIT. See [LICENSE](LICENSE).
