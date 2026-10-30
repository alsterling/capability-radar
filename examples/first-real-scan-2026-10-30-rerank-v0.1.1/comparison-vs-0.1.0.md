# 0.1.1 rerank vs 0.1.0 — first real scan, 2026-10-30

Same 59 records, same profile, same date. Inputs differ only by the `capability` and `owned` annotations. 0.1.0 numbers come from running the 0.1.0 code on the original scan file.

## Summary

| | 0.1.0 | 0.1.1 |
|---|---|---|
| Capability ranking | written by hand ([`top-opportunities.md`](../first-real-scan-2026-10-30/top-opportunities.md)) | `capradar opportunities` (25 capability groups) |
| Candidates at maximum `job_fit` | **46 of 58** | **8 of 58** |
| Distinct `job_fit` values | 4 (0, 0.5, 1.0, 1.5 points) | 15 (0–1) |
| Verdicts USE / TEST / WATCH / KEEP / IGNORE | 5 / 26 / 19 / – / 8 | 1 / 26 / 18 / 5 / 8 |
| Stack relation | IN_STACK / OVERLAP / NONE / UNKNOWN | 15 owned · 3 complements · 37 duplicates (29 of them only partial, native PARTIAL) · 3 new |
| Re-ingest of the same file | added a scan record, incremented `seen_count` | skipped; ledger byte-identical |

## Top 10 capability opportunities

| 0.1.1 # | Capability (CLI) | Score | Coverage | Verdicts | Benchmark | 0.1.0 hand-written # |
|---|---|---|---|---|---|---|
| 1 | measuring whether an AI capability helps | 8.16 | PARTIAL | TEST 3 | NO | 1 |
| 2 | office document creation | 7.79 | PARTIAL | TEST 2 | NO | — (new) |
| 3 | research to presentation decks | 7.79 | PARTIAL | TEST 2, WATCH 1 | YES | 9 |
| 4 | document-to-structured-text conversion | 7.66 | PARTIAL | TEST 1, IGNORE 1 | NO | 8 |
| 5 | portable extension standards (Skills, MCP) | 7.64 | PARTIAL | USE 1, WATCH 1 | NO | — (new) |
| 6 | human-quality writing | 7.56 | PARTIAL | TEST 1 | YES | 4 |
| 7 | context and token efficiency | 6.94 | PARTIAL | TEST 3, WATCH 1, IGNORE 1 | YES | 2 |
| 8 | model routing for cost and quality | 6.85 | PARTIAL | TEST 2 | YES | 6 |
| 9 | recurring workflow automation | 6.62 | COVERED | TEST 3, WATCH 2, KEEP 1 | YES | 7 |
| 10 | email and calendar management | 6.51 | PARTIAL | TEST 1 | NO | — (new) |

Dropped out of the top 10 relative to the hand-written list: **vetting third-party skills, plugins and MCP servers** (hand #3 → CLI #11, 6.46), **cited web research** (hand #5 → #16, 5.22, COVERED by owned built-in deep research), **proactive persistent personal agent** (hand #10 → #17, 4.86, all WATCH).

## Owned products that moved to KEEP

| Product | 0.1.0 | 0.1.1 |
|---|---|---|
| Claude Code cloud sessions and scheduled tasks | USE | KEEP |
| Codex cloud tasks and automations | USE | KEEP |
| GPT-6 family in ChatGPT and Codex | USE | KEEP |
| Built-in deep research in ChatGPT and Claude | USE | KEEP |
| ChatGPT scheduled tasks | WATCH | KEEP |

The only remaining USE is the Agent Skills open standard (improvement YES). The Agents lane is no longer headed by two owned items; it now starts with Claude Duet, Claude Managed Agents and Hermes Agent (all WATCH), and the owned items appear on a separate "Keep" line. The Models lane is no longer headed by GPT-6 (score 4.5 in 0.1.0); Claude 5.5 routing leads.

## Overlap scoring

Overlap now costs at most one penalty, and only for `DUPLICATES_CURRENT_STACK`. 47 of 58 entries changed overlap points:

- **15 owned features** went from −2.5 (native −1.5 plus stack −1.0) to 0, among them skill-creator evals, Claude 5.5 tiers, Claude Slides/Docs/Design, Claude Cowork, the LSP plugins, email/calendar connectors and Claude scheduled tasks. **3 complements** (Agent Skills standard, anthropics/skills, Claude Duet) also went to 0.
- **21 partial overlaps** (native PARTIAL plus a named owned tool) went from −1.5 to −0.5: e.g. Docling, Humanizer, context-mode, RTK, n8n.
- **8 full duplicates** went from −2.5 to −1.5 (e.g. Google Jules, OpenCode, GitHub Copilot coding agent, NotebookLM, GitHub MCP Server).

This materially changed the product-level ranking. The CLI's product top 10 gained three owned features that were the opportunity but had been double-penalized (Claude Slides/Docs/Design, Claude Cowork, the LSP plugins) and lost promptfoo, Chrome DevTools MCP and the Claude plugin directory (now #11–#14). SkillsBench moved from #1 to #6. At capability level, overlap acts only through each group's best candidates and through weak share (IGNORE or full duplicates).

One wrong classification was found and fixed during the rerank: `GitHub MCP Server` matched the stack item `GitHub` because the dedupe key drops "MCP" and "Server" (it was IN_STACK in 0.1.0 too). Stack matching now compares every word, so it is a duplicate of GitHub, not an owned item. Its verdict (IGNORE) did not change.

## Answers

1. **New top 10:** see the table above.
2. **Changes vs the hand-written top 10:** measuring stays #1. Seven of the ten hand-written capabilities stay in the top 10 in a different order (presentation decks and document conversion rise; context/token efficiency falls from #2 to #7). Office document creation, portable extension standards and email/calendar enter. Extension vetting, cited web research and the persistent personal agent leave.
3. **USE → KEEP:** four owned products (Claude Code cloud sessions, Codex cloud tasks, GPT-6 family, built-in deep research); ChatGPT scheduled tasks went WATCH → KEEP.
4. **Maximum job_fit:** 8 of 58 (0.1.0: 46 of 58).
5. **Overlap scoring changed rankings:** yes, at product level (see above). Owned features that are themselves the opportunity are no longer pushed down.
6. **Obviously wrong opportunities:** none is plainly wrong, but three are judgment calls to note:
   - *Office document creation (#2)* rests on an owned feature whose own reason says "the gap is usage, not tooling". Coverage is PARTIAL (not COVERED) because the Skill marked improvement YES.
   - *Portable extension standards (#5)* is driven by one USE item, a format convention to follow when writing Skills rather than a gap.
   - *Extension vetting (#11)* is lower than a reviewer would put it. The profile names security only as a **constraint**, and job fit reads jobs only. Its best candidate matches the "discovering and evaluating" job weakly (2 shared terms).
7. **Token/context efficiency:** still in the top 10 (#7, 6.94) with three TEST candidates and STRONG best evidence, but no longer top 3. Its relevance is 0.55: the profile mentions token/context cost only in the personal-productivity job, not the coding job.
8. **Human-quality writing:** still strong (#6, 7.56). Relevance 1.0, held back by WEAK evidence (one popular, unevaluated candidate).
9. **Extension/plugin/MCP vetting:** no longer among the strongest (#11, 6.46). The reasons are in item 6.
