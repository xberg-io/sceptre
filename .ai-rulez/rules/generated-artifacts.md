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

- `plugin/.ai-rulez/` is the source of `plugin/**` (except `plugin/README.md`), `skills/**` and the root `.claude-plugin/` and `.agents/plugins/` marketplaces. Regenerate with `task plugin:generate`; `task plugin:verify` and the `ai-rulez-plugin-verify` commit hook byte-check them. Never edit them by hand.
- `docs-site/src/content/docs/more/changelog.md` is generated from `CHANGELOG.md`: run `task docs:changelog` after editing it (gate `task docs:changelog:check`).
- `benchmarks/published/latest.json` and the `generated:benchmark-headline` blocks in README.md and the docs benchmarks page come from `task python:publish` (ADR 0030; gate `task python:publish:check`). Never edit the numbers by hand.
