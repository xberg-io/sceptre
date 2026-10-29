---
type: Decision
title: Generated Artifacts
paths:
  - "plugin/**"
  - "skills/**"
  - ".claude-plugin/**"
  - ".agents/plugins/**"
  - "CHANGELOG.md"
  - "docs-site/src/content/docs/more/changelog.md"
  - "docs-site/src/content/docs/reference/benchmarks.mdx"
  - "benchmarks/**"
  - "README.md"
x-ai-rulez:
  kind: rule
  id: generated-artifacts
  metadata:
    priority: high
---

# Generated Artifacts

- `plugin/.ai-rulez/` is the source of `plugin/**` (except `plugin/README.md`), `skills/**` and the root `.claude-plugin/` and `.agents/plugins/` marketplaces. Regenerate with `mise run plugin:generate`; `mise run plugin:verify` and the `ai-rulez-plugin-verify` commit hook byte-check them. Never edit them by hand.
- `docs-site/src/content/docs/more/changelog.md` is generated from `CHANGELOG.md`: run `mise run docs:changelog` after editing it (gate `mise run docs:changelog:check`).
- `benchmarks/published/latest.json` and the `generated:benchmark-headline` blocks in README.md and the docs benchmarks page come from `mise run python:publish` (ADR 0030; gate `mise run python:publish:check`). Never edit the numbers by hand.
