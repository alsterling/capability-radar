# First real scan — 2026-10-30

First real-use run of Capability Radar 0.1.0, for a generic technically sophisticated knowledge worker / builder whose stack is ChatGPT, Claude, Claude Code, Codex and GitHub. Discovery and ranking only: nothing was installed, built or benchmarked.

| File | What it is |
|---|---|
| [`profile.md`](profile.md) | The profile (a role, not a person; public-safe) |
| [`scan-plan-2026-10-30.json`](scan-plan-2026-10-30.json) | Plan written by `capradar scan --all --top 10` |
| [`scan-2026-10-30.json`](scan-2026-10-30.json) | Candidate file from the Skill: 59 records, all queries, sources with tier/type/read method, saturation per lane |
| [`ledger-2026-10-30.json`](ledger-2026-10-30.json) | Ledger after ingest + dedupe: 58 entries |
| [`report-2026-10-30.md`](report-2026-10-30.md) | `capradar report --top 10` output |
| [`reverify-2026-10-30.txt`](reverify-2026-10-30.txt) | `capradar reverify` as of the scan date and as of 2026-12-20 |
| [`top-opportunities.md`](top-opportunities.md) | Hand-written capability-level ranking across lanes (the CLI ranks products only) |
| [`radar-evaluation.md`](radar-evaluation.md) | How the radar performed, and parked follow-ups |
| [`clean-install-validation.md`](clean-install-validation.md) | Fresh-clone install and CLI validation |

Reproduce the report from the saved files:

```bash
python -m capradar init --dir /tmp/radar-check
```

```bash
cp examples/first-real-scan-2026-10-30/profile.md /tmp/radar-check/profile.md
```

```bash
python -m capradar ingest --dir /tmp/radar-check examples/first-real-scan-2026-10-30/scan-2026-10-30.json --as-of 2026-10-30
```

```bash
python -m capradar report --dir /tmp/radar-check --top 10 --as-of 2026-10-30
```

Facts in this folder are a snapshot from one session and will go stale; that is what `reverify` is for.
