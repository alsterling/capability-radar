# Top opportunities across all lanes — 2026-10-30

Profile: [`profile.md`](profile.md) (generic technical knowledge worker / builder; current stack ChatGPT, Claude, Claude Code, Codex, GitHub).
Evidence: [`scan-2026-10-30.json`](scan-2026-10-30.json) (58 candidates, 8 lanes) and the CLI report [`report-2026-10-30.md`](report-2026-10-30.md).

The CLI's own "TOP OPPORTUNITIES" list ranks **products**. This file ranks **capabilities** (the job that would get better), with the products found as candidates for each. It is discovery only: nothing here has been installed, built or benchmarked.

## Ranking

| # | Capability opportunity | Candidates found | Native stack covers it? | Benchmark next? | Future public Skill/tool? |
|---|---|---|---|---|---|
| 1 | Measuring whether a new AI capability actually helps | skill-creator evals (owned), SkillsBench, promptfoo | Partly (skill-creator) | It *is* the benchmark | **Strong** |
| 2 | Context and token efficiency in coding agents | Claude Code LSP plugins (owned), context-mode, RTK, Serena; Haiku 5.5 routing | Partly (tool search, `/context`, LSP plugins) | **Yes** | Good, as an evaluation; crowded as a tool |
| 3 | Vetting third-party Skills, plugins and MCP servers before install | Claude plugin directory safety scan; Enterprise-only scanning; security studies | Partly (reviewed directory) | No; needs a targeted scan first | **Strong** |
| 4 | Human-quality long-form writing | Humanizer (62k stars, unevaluated) | Partly (styles, editing) | **Yes** (blind A/B) | Possible; crowded, evidence is the gap |
| 5 | Research evidence quality: better search and citation checking | Perplexity Search API, Exa, Parallel; built-in deep research (owned); Gemini Deep Research Max | Mostly (built-in deep research) | **Yes** | Moderate (citation checking) |
| 6 | Model routing to cut cost and plan-limit use | Claude 5.5 tiers (owned), Max/Team monthly API credits | Yes, needs deliberate use | **Yes** | Low–moderate |
| 7 | Recurring automation of knowledge work | Claude scheduled tasks, ChatGPT scheduled tasks, Codex automations (all owned), claude-code-action, n8n | Mostly | One workflow, light | Low |
| 8 | Structured document ingestion | Docling (strong independent benchmark), anthropics/skills document skills | For single files, yes | No (evidence exists) | Low |
| 9 | Research → presentation | Claude Slides/Docs (owned), ChatGPT Slides (plan-gated), Slidev | Mostly | Light (one real deck) | Low |
| 10 | Proactive persistent personal agent | Claude Duet (preview), ChatGPT dots (Pro), Hermes Agent, OpenClaw, Claude Managed Agents | Arriving (previews in owned plans) | Later | Low now |

## Detail

### 1. Measuring whether a new AI capability actually helps
- **Why it matters.** 14 of this scan's 26 TEST verdicts carry `benchmark_needed: YES`. Popularity is a poor signal: a 3,984-skill audit found 13.4% with a critical issue, and SkillsBench (peer-reviewed) found curated skills add about 16 points on average while self-generated skills add nothing. Without a cheap way to measure, every other item on this list stays a guess. It is also the profile's tenth job.
- **Found.** skill-creator eval/benchmark mode (owned via Claude Code); SkillsBench's method and verifiers; promptfoo for provider-neutral comparisons (OpenAI-acquired, still MIT).
- **Native coverage.** Partial: skill-creator measures one Skill in Claude Code. Nothing owned compares the same job across Claude, ChatGPT and Codex.
- **Benchmark next?** It is the instrument for the others. First step: run skill-creator's benchmark on one candidate from #2 or #4.
- **Public product?** Strong. Capability Radar's README lists "no benchmark harness yet" as a limitation; a small, job-level A/B harness is the natural next public piece.

### 2. Context and token efficiency in coding agents
- **Why it matters.** Coding is the highest-frequency job, and context limits drive both cost and quality. One guide estimates tool output at 60–80% of context; output tokens are a small share (independent re-measurements put output at 0.6–2.5% of spend), which is why output-only tricks like Caveman were rated IGNORE.
- **Found.** Official LSP plugins (independent CircleCI benchmark: ahead of grep on tokens and price, modest margin); context-mode (vendor claim 98% less tool output); RTK (vendor claim 60–90% on Bash output; Bash only); Serena (README claims). Native: tool search defers MCP schemas; `/context` shows usage; Haiku 5.5 for cheap subagents.
- **Native coverage.** Partial. Only the LSP plugins have independent evidence.
- **Benchmark next?** Yes. Same repo, same tasks: baseline vs LSP plugins vs context-mode vs RTK; measure task success first, then tokens.
- **Public product?** Good as a published, reproducible evaluation. Weak as yet another compression tool (RTK has 85k stars, context-mode 33k).

### 3. Vetting third-party Skills, plugins and MCP servers
- **Why it matters.** Every adoption in lanes 1–3 runs third-party code with the agent's permissions. Studies in 2026 found 157 confirmed malicious skills among 98k, and nearly half of 33k MCP builds with security concerns. Claude's automatic scanning is Enterprise-only; individuals rely on manual review.
- **Found.** Claude plugin directory (submissions safety-scanned); Enterprise scanning (beta); vendor audits (Snyk, ESET).
- **Native coverage.** Partial: install from the reviewed directory when possible.
- **Benchmark next?** Not yet. This scan did not survey individual-user scanners; a targeted scan should come before any evaluation.
- **Public product?** Strong: underserved for individuals and adjacent to what Capability Radar already does (it evaluates before you install).

### 4. Human-quality long-form writing
- **Why it matters.** Writing is a primary job, and generic AI prose is a known quality problem.
- **Found.** Humanizer (62.4k stars, active, MIT; built on Wikipedia's "Signs of AI writing"). No controlled study shows it helps.
- **Native coverage.** Partial: owned assistants can follow style instructions.
- **Benchmark next?** Yes: blind A/B of raw vs edited drafts on real pieces, judged by readers rather than detectors.
- **Public product?** Possible but crowded; the evidence gap, not the tooling gap, is the opening. (Not to be built in this task.)

### 5. Research evidence quality
- **Why it matters.** Deep research is the first listed job. Built-in deep research is competitive in the small tests found, but citation accuracy is still checked by hand.
- **Found.** Perplexity Search API (top of the independent Artificial Analysis Search Index), Exa (leads an independent factual-lookup board), Parallel (close behind); Gemini Deep Research Max as a second opinion.
- **Native coverage.** Mostly. The gap is checking that each cited claim is supported, not finding sources.
- **Benchmark next?** Yes, with a fixed question set comparing built-in search against one API. Do not test three overlapping APIs at once.
- **Public product?** Moderate: a citation-checking Skill is plausible.

### 6. Model routing for cost and plan limits
- **Why it matters.** The owned plans now span very different price points (Opus 5.5 at $4/$20 per M tokens, Haiku 5.5 the cheapest); Max/Team plans include monthly API credits that can fund experiments.
- **Native coverage.** Yes; the opportunity is deliberate configuration, not a new tool.
- **Benchmark next?** Yes, on the profile's own coding/research tasks; independent scores run below vendor scores.
- **Public product?** Low–moderate.

### 7. Recurring automation
- **Native coverage.** Mostly. Claude, ChatGPT and Codex all schedule tasks; claude-code-action joins Claude Code and GitHub. n8n only for deterministic multi-app flows the assistants cannot do reliably. Pick one scheduler to avoid duplicate jobs.
- **Benchmark next?** Light: one real recurring workflow.
- **Public product?** Low.

### 8. Structured document ingestion
- **Native coverage.** Single files: yes. Batch or structure-preserving conversion: Docling, backed by an independent 12-engine benchmark (MarkItDown much weaker on headings and tables).
- **Benchmark next?** Not needed beyond a smoke test.
- **Public product?** Low; solved by existing open source.

### 9. Research → presentation
- **Native coverage.** Mostly: Claude Slides/Docs in any conversation (owned). ChatGPT Slides needs Pro or above. Slidev for version-controlled technical decks.
- **Benchmark next?** Light: build one real deck in Claude Slides before adding any tool.
- **Public product?** Low; the category is being absorbed into the assistants.

### 10. Proactive persistent personal agent
- **Native coverage.** Arriving: Claude Duet (US waitlist research preview) and ChatGPT dots (Pro only). Self-hosted options (Hermes Agent, OpenClaw) conflict with the profile's security constraint.
- **Benchmark next?** Later, once Duet leaves preview.
- **Public product?** Low now. Claude Managed Agents is the substrate if a persistent worker is built later.

## Top 3 to evaluate next

1. **Context and token efficiency (#2)**: highest-frequency job, measurable, and only one candidate has independent evidence.
2. **Human-quality writing (#4)**: a primary job with a popular candidate and zero outcome evidence; a blind A/B settles it quickly.
3. **Extension vetting (#3)**: gates every future install and is the clearest public-product gap. Run a targeted scan of individual-user scanners first.

Use #1 (owned skill-creator benchmark mode) as the instrument for the first two.

## Already covered by the current stack

Background coding execution (Claude Code cloud and scheduled tasks, Codex automations) · deep research (ChatGPT, Claude) · GitHub access (GitHub MCP Server adds nothing) · coding agents (Copilot coding agent, Jules and OpenCode duplicate Claude Code and Codex) · frontier models (GPT-6 family, Claude 5.5 family) · single-file document reading · email/calendar connectors · decks (Claude Slides) · scheduled assistant tasks.
