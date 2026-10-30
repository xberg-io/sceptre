---
status: accepted
date: 2026-10-27
decision-makers: ["Na'aman Hirschfeld"]
amends: ["0006"]
---

# Shared agent governance from agent-conventions modules

## Context and Problem Statement

[ADR 0006](0006-ai-rulez-for-agent-config.md) made `.ai-rulez/` the source of truth for agent
configuration, with rules, context and skills written in this repository. Most of those rules are
organization conventions that every xberg-io repository carries, and copies of the same rule drift
apart when each repository edits its own.

## Decision Drivers

* An organization rule has one source and reaches every repository the same way.
* sceptre keeps its own rules for decisions that are specific to it.
* The governance version can be moved deliberately and checked in CI.

## Considered Options

* Keep every rule in this repository's `.ai-rulez/` (status quo from ADR 0006).
* Include the shared agent-conventions modules by version range, and keep only sceptre's own rules
  locally.

## Decision Outcome

Chosen option: "include the shared agent-conventions modules by version range, and keep only
sceptre's own rules locally", because an organization rule then has one source and reaches every
repository the same way, while sceptre-specific rules stay here.

* `.ai-rulez/config.toml` includes `modules/core`, `modules/languages`, `modules/cicd` and
  `modules/docs-sites` from `https://github.com/xberg-io/agent-conventions.git` at version `^1`, with
  `merge_strategy = "local-override"` (734ab13 pinned a commit first; adda000, 2026-10-27, moved to
  the version range so `ai-rulez update` moves the pin).
* Rules local to `.ai-rulez/rules/`, such as `adr-discipline`, cover sceptre's own conventions.
* The governance actions run from their `@v1` major tag.

The organization decision is org ADR "ai-rulez and agent-conventions modules" (agent-conventions
`adrs/`). This ADR amends ADR 0006 only in where the shared rules come from; ai-rulez remains the
generator, and generated files remain unedited outputs.

### Consequences

* Good, because a rule change lands once in agent-conventions and reaches sceptre with
  `ai-rulez update` and `ai-rulez lock`.
* Bad, because a local rule that conflicts with a shared one silently wins under
  `local-override`, so local rules must be reviewed against the shared modules.

### Confirmation

`.github/workflows/ai-rulez-validation.yml` runs `xberg-io/actions/validate-ai-rulez@v1` and the
agent-conventions `context-exposure@v1` action, and the poly `ai-rulez-validate` hook checks the
generated output on commit.
