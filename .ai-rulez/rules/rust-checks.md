---
type: Decision
title: Rust Checks
paths:
  - "**/*.rs"
  - "**/Cargo.toml"
x-ai-rulez:
  kind: rule
  id: rust-checks
  metadata:
    priority: high
---

# Rust Check Discipline

- Write a failing test first when the change is observable from the public API, the CLI, or the MCP
  surface. Those three are sceptre's contract; everything else is an implementation detail.
- Silence a clippy lint with `#[allow(...)]` only when the warning is wrong, with a one-line `//`
  justification ending in `~keep`.
- After adding or changing any dependency, run `cargo upgrade --incompatible` so pins stay current,
  then rebuild.
- `cargo test --workspace` is the release gate, not a per-commit gate. Run it when the change
  touches the pipeline, before a release, or when asked.
