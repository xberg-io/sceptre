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

- Architecturally significant decisions are recorded as MADR ADRs under `adrs/` (`NNNN-title.md`, numbered sequentially).
- Add a new ADR when you choose between real alternatives with lasting consequences: a dependency or backend, a pipeline algorithm, a public API shape, a model source, a build/target strategy.
- Front-matter `status:` is lowercase: `proposed`, `accepted`, `rejected`, `superseded by NNNN`. There is no template; copy the shape of a recent ADR.
- Do not rewrite the history of an accepted ADR. To reverse a decision, add a new ADR and set the old one's status to `superseded by NNNN`; a partial change says it amends ADR NNNN.
- Add the row to the `adrs/README.md` index in the same change.
- Keep code comments free of decision rationale that belongs in an ADR — link to the ADR instead.
