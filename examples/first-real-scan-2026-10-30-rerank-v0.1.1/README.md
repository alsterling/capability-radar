# First real scan, reranked with 0.1.1 — 2026-10-30

The [first real scan](../first-real-scan-2026-10-30/) re-ingested and reranked with Capability Radar 0.1.1. **No new market search:** the candidates, sources and judgments are the saved 0.1.0 scan. The 0.1.0 artifacts are unchanged; a test pins their hashes.

| File | What it is |
|---|---|
| [`capability-annotations.json`](capability-annotations.json) | The only new input: a `capability` for each of the 59 records, and `owned: YES` for 15 of them. Assigned by hand from each record's own `job` field and, for `owned`, only where the saved scan's description or reason already says the item is owned or included in the current plan |
| [`scan-2026-10-30-annotated.json`](scan-2026-10-30-annotated.json) | The saved scan plus those two fields. A test checks that no other field changed |
| [`ledger-2026-10-30.json`](ledger-2026-10-30.json) | Ledger after 0.1.1 ingest + dedupe: 58 entries, with job fit and matched jobs |
| [`report-2026-10-30.md`](report-2026-10-30.md) | `capradar report --top 10` (product level per lane, KEEP listed apart, capability summary) |
| [`opportunities-2026-10-30.md`](opportunities-2026-10-30.md) | `capradar opportunities --top 10`: the capability-level ranking the CLI now produces |
| [`comparison-vs-0.1.0.md`](comparison-vs-0.1.0.md) | What changed against the 0.1.0 report and the hand-written top-10 |

The profile is the 0.1.0 one: [`../first-real-scan-2026-10-30/profile.md`](../first-real-scan-2026-10-30/profile.md).

Reproduce (a test does the same and compares the output byte for byte):

```bash
python -m capradar init --dir /tmp/radar-rerank
```

```bash
cp examples/first-real-scan-2026-10-30/profile.md /tmp/radar-rerank/profile.md
```

```bash
python -m capradar ingest --dir /tmp/radar-rerank examples/first-real-scan-2026-10-30-rerank-v0.1.1/scan-2026-10-30-annotated.json --as-of 2026-10-30
```

```bash
python -m capradar dedupe --dir /tmp/radar-rerank
```

```bash
python -m capradar report --dir /tmp/radar-rerank --top 10 --as-of 2026-10-30
```

```bash
python -m capradar opportunities --dir /tmp/radar-rerank --top 10 --as-of 2026-10-30
```

Ingesting the same file again prints `already ingested (identical content); skipped` and leaves the ledger unchanged.

Facts in this folder are a snapshot from one session and will go stale; nothing here was installed or benchmarked.
