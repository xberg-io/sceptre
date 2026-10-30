---
status: accepted
date: 2026-10-14
decision-makers: ["Na'aman Hirschfeld"]
---

# Agent plugin and public skills distribution

## Context and Problem Statement

sceptre ships an MCP server ([ADR 0005](0005-mcp-as-feature-module-and-subcommand.md)) and skills
that teach a coding agent to use it. Each agent runtime (Claude, Codex, Cursor, Gemini, Kimi,
OpenCode, Factory, Hermes, Pi, Agent Plugins, Copilot) expects its own manifest layout, and
maintaining a hand-written bundle per runtime means one more copy of the same skill for each.

## Decision Drivers

* One source for skills and plugin content, regenerated for every runtime.
* A published bundle and the public skills must match the source they were built from.

## Considered Options

* Hand-maintain a plugin bundle per agent runtime.
* Generate every runtime bundle under `plugin/` with `ai-rulez generate --plugin` from
  `plugin/.ai-rulez/`, and export the same skills to `skills/`.

## Decision Outcome

Chosen option: "generate every runtime bundle under `plugin/` with `ai-rulez generate --plugin`
from `plugin/.ai-rulez/`, and export the same skills to `skills/`", because skills and plugin
content then have one source, and freshness is verifiable against it.

* The canonical plugin content lives under `plugin/.ai-rulez/`; `ai-rulez generate --plugin`
  writes the per-runtime manifests under `plugin/` and the marketplace indexes
  (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`) (f84a6ed, 2026-10-14).
* `scripts/sync_public_skills.py` exports the native ai-rulez skills to `skills/` without a
  second source tree, and records the files it owns in a manifest so stale files can be pruned.
* `.github/workflows/plugin-artifacts.yaml` packages every supported runtime for an existing
  release tag and attaches the verified archive, with ai-rulez pinned on that release path.

The organization decision on shared distribution is org ADR "shared assets and distribution"
(agent-conventions `adrs/`).

### Consequences

* Good, because adding or editing a skill is one change, and every runtime bundle follows.
* Bad, because the generated bundle files are many and must never be edited by hand; poly
  excludes them so formatting cannot break their provenance.

### Confirmation

`.github/workflows/ci-plugin.yaml` runs `scripts/tests/test_public_skills.py` and
`scripts/sync_public_skills.py --check`, and `ai-rulez verify --plugin` compares the bundle with
the source output and provenance.
