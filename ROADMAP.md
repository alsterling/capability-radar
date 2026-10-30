# Roadmap

Direction and decisions recorded at the 0.1.1 public alpha. Nothing below is implemented yet unless it says so. Priorities may change based on Capability Radar's own evidence and on platform changes.

## Release priority

Capability Radar 0.1.1 public alpha ships first. It is not delayed for cross-platform wrappers.

## Provider-neutral core

Capability Radar's long-term core stays provider-neutral. These parts must not depend on Claude unless there is no reasonable alternative:

- candidate schema and data model
- normalization
- dedupe
- evidence handling
- ranking
- capability opportunity grouping
- current-stack comparison
- ledger
- reverify
- reports

Claude / Claude Code is the **first supported host and distribution wrapper**, not the permanent architectural boundary of the product.

## Architecture rule

```
provider-neutral capradar core  →  host-specific Skill / plugin / wrapper
```

- Platform-specific wrappers stay thin: they handle discovery prompts, host install format and invocation, and call the core.
- Adding a new platform must not require rewriting discovery, ranking, ledger or reverify logic.

## Future host compatibility

After the 0.1.1 public alpha, investigate and add host wrappers incrementally, without rewriting the core. Preferred order today:

1. Grok Build compatibility
2. OpenAI Codex / Agent Skills compatibility
3. ChatGPT plugin / wrapper compatibility
4. Gemini CLI / Antigravity compatibility

**None of these is supported yet.** Only Claude Code is tested (see the README's Limitations). The order may change based on Capability Radar evidence and platform changes.

## Portability metadata (future)

Candidate records should eventually carry a portability / host-compatibility field, with values such as:

- Claude
- Codex / OpenAI
- ChatGPT
- Grok
- Gemini
- other relevant hosts

Future work only; the field is not part of the current schema.
