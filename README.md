# Capability Radar

**Status: 0.1.0 public alpha candidate. Not production-ready.**

An on-demand radar for AI capabilities: Skills, plugins/connectors, MCP servers, agents, open-source projects, model features, research/search tools and automation tools. It checks what you already have, searches current public sources, dedupes wrappers and forks, ranks by **evidence rather than popularity**, keeps a local ledger, and tells you what to re-verify.

It never installs anything. "Nothing worth changing" is a valid result.

## How it works

| Layer | What | Where |
|---|---|---|
| Discovery and judgment | A Skill your assistant runs: checks your stack, searches several source types per lane, verifies, fills a candidate file | `skills/scan/SKILL.md` |
| Deterministic core | A stdlib Python CLI: plan, ingest, dedupe, rank, report, reverify. No network calls, no dependencies | `capradar/` |
| Memory | JSON ledger + Markdown profile and reports in a local workspace (`./radar`) | your disk |

## Install

**As a Claude Code plugin** (gives `/capability-radar:scan`):

```bash
claude plugin marketplace add <owner>/capability-radar
```

```bash
claude plugin install capability-radar@capability-radar
```

**CLI only** (Python 3.10+, no dependencies):

```bash
git clone https://github.com/<owner>/capability-radar && cd capability-radar
```

```bash
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
python -m capradar reverify [--json] [--write-plan]
```

All commands take `--dir` (workspace; default `./radar` or `$CAPRADAR_HOME`) and `--as-of YYYY-MM-DD`.

## Profile

`radar/profile.md` is plain Markdown: `## Jobs` (one recurring job per bullet), `## Current stack` (`Name | lane | what it covers`), `## Constraints`. The radar uses it for fit and current-stack overlap. A synthetic example is in [`capradar/data/profile.example.md`](capradar/data/profile.example.md). Keep secrets and client names out of it.

## Lanes

Eight default lanes, defined as data in [`capradar/data/categories.json`](capradar/data/categories.json) (copied to `radar/config.json` on `init`): Skills · Plugins / Connectors · MCP · Agents / persistent workers · GitHub / OSS · Models / native features · Research / search tools · Automation / workflow tools. Add a lane by adding an entry to `config.json`; no code change.

## Candidate fields

Name, lane, exact job/capability, description, source URLs with tier (`TIER1_OFFICIAL` / `TIER2_ECOSYSTEM` / `TIER3_PRACTICAL`) and type, status/maintenance, last activity, version, popularity signals, evidence quality (`STRONG` / `MODERATE` / `WEAK` / `ANECDOTAL`), cost, privacy, permissions, native overlap, overlaps with, relation to a current tool, recommendation, reason, benchmark needed, improvement opportunity (`YES` / `NO` / `UNKNOWN`), last verified, reverify date/trigger, aliases. Anything not established is `UNKNOWN`. `capradar scan` writes the full contract into each scan plan.

## Verdicts and ranking

- **USE** adopt now · **TEST** try on a real job first · **WATCH** not yet · **IGNORE** skip.
- The Skill proposes a verdict; the CLI **caps** it by evidence. No source caps a verdict at WATCH. WEAK, ANECDOTAL or UNKNOWN evidence, or a needed benchmark, caps it at TEST. ARCHIVED or DEPRECATED means IGNORE. Caps are shown in the report.
- Score = evidence + source tier + source diversity + maintenance + improvement + job fit − native/stack overlap − staleness + popularity. Popularity is capped at 0.75 points, below one evidence step, and never changes a verdict.
- **Top opportunities** = improvement `YES`, verdict USE/TEST, not already in your stack.

## Ledger and dedupe

`radar/ledger.json` keeps every candidate ever seen: aliases, verdict history (prior verdict), sources, cost/privacy/permissions, version, last verified, reverify date/trigger, and scan history. Duplicates are merged within a lane by normalized name ("Acme MCP Server" = "acme-mcp"), aliases, `duplicate_of`, or the candidate's own repository URL. A shared list page never merges two tools. A newer verification wins; UNKNOWN never overwrites a known value; a weaker-tier record never overwrites a stronger one from the same day.

## Reverify

`capradar reverify` lists stale entries (older than the lane's freshness window, or never verified), entries whose reverify date has passed, entries with a reverify trigger to check, and lanes needing a fresh scan. There is no scheduler: run it when you like, or ask the Skill to refresh what it lists.

## Example

The first dogfood run (2026-10-30, synthetic profile, 8 lanes, 35 candidates, 1 merged duplicate, 34 ledger entries):
- [`examples/report-2026-10-30.md`](examples/report-2026-10-30.md): the report
- [`examples/scan-2026-10-30.json`](examples/scan-2026-10-30.json): the candidate file the Skill wrote, with queries and sources opened
- [`examples/ledger-2026-10-30.json`](examples/ledger-2026-10-30.json), [`examples/scan-plan-2026-10-30.json`](examples/scan-plan-2026-10-30.json), [`examples/reverify-example.txt`](examples/reverify-example.txt)

The example is a snapshot from one session. Facts in it will go stale; that is what `reverify` is for.

## Tests

```bash
python -m unittest discover -s tests
```

Stdlib only, no network. They cover ingest, normalization, alias/dedupe, ranking, top-N, lane filtering, all four verdicts, unknown fields, stack overlap, ledger persistence, stale/reverify detection, report generation, and public-safety checks: no personal markers, no network code, no candidate names hardcoded in code.

## Limitations

- **Discovery quality depends on the assistant running the Skill** and its search tools. One scan samples each lane; it is not a census.
- **Judgments are the Skill's** (evidence quality, improvement opportunity). The CLI only caps them and ranks consistently. Scores are heuristic, not calibrated.
- **Not measured on your jobs.** TEST means "worth a short trial", not "proven better". The radar has no benchmark harness yet.
- **Dedupe is rule-based.** Renamed projects with no shared name, alias or repo are not caught; mark them with `duplicate_of`.
- **No scheduler, server or database**, by design.
- Plugin packaging has been checked against the documented format but not yet installed from a hosted marketplace.

## Privacy

See [PRIVACY.md](PRIVACY.md). Short version: the CLI makes no network calls and sends no telemetry; your workspace stays on your disk; nothing is installed or authorized for you.

## License

MIT. See [LICENSE](LICENSE).
