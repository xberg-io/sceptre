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

- The public API, the CLI and the MCP surface are sceptre's contract; everything else is an implementation detail.
- After adding or changing a dependency, run `cargo upgrade --incompatible -p <crate>` (cargo-edit) for that crate only. A workspace-wide bump is `mise run upgrade`, committed on its own.
