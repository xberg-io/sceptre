---
type: Decision
title: Adr Discipline
paths:
  - "adrs/**"
  - "crates/**"
  - "Cargo.toml"
  - ".github/workflows/**"
x-ai-rulez:
  kind: rule
  id: adr-discipline
  metadata:
    priority: high
---

# ADR Discipline

- Architecturally significant decisions are recorded as MADR ADRs under `adrs/` (`NNNN-kebab-title.md`, numbered sequentially from `0000`).
- Add a new ADR when you choose between real alternatives with lasting consequences: a dependency or backend, a pipeline algorithm, a public API shape, a model source, a build/target strategy.
- Start from `adrlint new "<title>"`, which writes the MADR template: `## Context and Problem Statement`, `## Considered Options`, `## Decision Outcome` opening with `Chosen option: "...", because ...`, and `### Consequences` and `### Confirmation` under it. Confirmation cites the file, test or CI gate that verifies the decision.
- Front-matter `status:` is one of `proposed`, `accepted`, `rejected`, `deprecated`, `superseded`; `date` is the day the decision was made; `decision-makers` is a list.
- Never edit an accepted ADR, not even to append a status note or amendment. A change is a new ADR: list partial changes in its `amends: ["NNNN"]`.
- To supersede ADR NNNN with a new ADR MMMM, accept MMMM with `supersedes: "NNNN"`, then `adrlint unlock adrs/NNNN-<slug>.md --reason "superseded by MMMM"`, set NNNN to `status: superseded` with `superseded-by: "MMMM"`, and run `adrlint lock`. Quote every ADR id in front matter.
- Add the row to the index in `docs-site/src/content/docs/reference/decision-records.mdx` in the same change; `adrs/` holds only ADRs.
- `adrlint lint` and `adrlint format --check` must pass; adrlint, not poly, owns the Markdown under `adrs/`.
- Keep code comments free of decision rationale that belongs in an ADR — link to the ADR instead.
