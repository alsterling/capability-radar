# Clean-install validation — Capability Radar 0.1.0

Date: 2026-10-30. Source: `main` at `5c7f4f0`. Environment: fresh clone in an empty temporary folder, fresh Python 3.13 virtual environment, no cached state, Linux.

**Result: PASS.** No blocking installation bug. Four friction points, listed below.

## Checks

| Check | Command | Result |
|---|---|---|
| Clone | `git clone -b main https://github.com/<owner>/capability-radar` | PASS (see friction 1: plain `git clone` gets a different branch) |
| Install (editable) | `pip install -e .` in a fresh venv | PASS; `capradar` entry point on PATH; `capradar --version` → `capradar 0.1.0` |
| Install (non-editable) | `pip install <clone>` in a second fresh venv | PASS; packaged `data/` files present (`init --example` copies the example profile) |
| No-install path | `python -m capradar …` from the repo folder | PASS; `radar/` is gitignored, working tree stays clean |
| Skill path | `PYTHONPATH=<plugin root> python -m capradar …` from another folder | PASS (this is the fallback `skills/scan/SKILL.md` gives) |
| `$CAPRADAR_HOME` | `CAPRADAR_HOME=<ws> python -m capradar rank …` | PASS |
| CLI imports | import every `capradar.*` module | PASS |
| Tests | `python -m unittest discover -s tests` | PASS, 37 tests, 0.18 s |
| `init` | `init --example`; second `init` | PASS; second run refuses with exit 1 and a clear message (`--force` keeps the ledger) |
| Example profile | `scan --all` → ingest `examples/scan-2026-10-30.json` → `dedupe` → `report` | PASS; 34 new, 1 merged, 0 rejected; report body is byte-identical to `examples/report-2026-10-30.md` |
| Report generation | `report --top 10` | PASS |
| Ledger persistence | re-run ingest in a new process on the existing ledger | PASS; 34 entries stay 34, sources deduped by URL, scan history appended |
| `reverify` | as of scan date and as of +70 days, with `--write-plan` | PASS; output matches `examples/reverify-example.txt`; future date flags 34 stale, 34 due, 8 lanes |
| Plugin manifest | `claude plugin validate <clone>` | PASS |
| Plugin install | `claude plugin marketplace add <local clone>` then `claude plugin install capability-radar@capability-radar` (isolated HOME) | PASS; plugin enabled; the cached plugin copy contains `capradar/`, so the Skill's `PYTHONPATH=<plugin root>` fallback runs |

## Friction

1. **The GitHub default branch is not `main`.** The remote `HEAD` points to `claude/v0.1.0-public-alpha` (the merged PR branch). A plain `git clone` checks that out. Its content is identical to `main` today, but the two will diverge with the next merge. Fix is a repository setting (default branch → `main`), not code.
2. **README install commands use placeholders and the repo is private.** `claude plugin marketplace add <owner>/capability-radar` and the clone URL need the real owner, and a private repo needs GitHub auth. The hosted-marketplace install was not exercised; the local-folder marketplace install was. README already says hosted install is untested.
3. **The README does not mention a virtual environment.** System `pip install -e .` worked here, but on distributions that mark system Python as externally managed (PEP 668) it is refused. One line ("use a venv") would prevent that.
4. **`python -m capradar` works only from the repo folder or after install.** The Skill documents the `PYTHONPATH=<plugin root>` fallback, and it worked, but a fresh assistant has to notice the `No module named capradar` error first.

Minor observations (not friction for a new user):

- Re-ingesting the same scan file counts as a second sighting (`seen_count` +1 and a second scan record). Entries are not duplicated.
- The shipped example scan file has a partial date (`"2026-04"`), which ingest warns about and stores as `UNKNOWN`. Correct behavior, slightly noisy for a first demo.

## Skill self-containment (fresh Claude Code context)

`skills/scan/SKILL.md` was followed literally, from a fresh context, to produce the real scan in this folder. It was sufficient: plan → stack check → discovery per lane → judgment → write → ingest → dedupe → report → reverify all ran without needing the README. Two gaps found during that run:

- It says every material claim needs "a source URL you actually opened". In this session the network policy blocked direct fetches of most hosts, so many pages could only be read through the search tool. The Skill gives no way to record that distinction; this run recorded it in each source's `note` (`fetched` or `search-read`).
- It asks for `last_activity` from the source. GitHub's REST API was unavailable; commit pages worked for most repos. The Skill names no fallback.

Neither blocks use.
