---
type: Decision
title: Module Size Cap
paths:
  - "crates/*/src/**/*.rs"
targets:
  - ".claude/rules/"
  - ".github/instructions/"
x-ai-rulez:
  kind: rule
  id: module-size-cap
  metadata:
    priority: critical
---

# Module Size Cap

- Every file under `crates/*/src/**/*.rs` is capped at **1000 lines**, enforced by the `max_lines` integration test (`crates/sceptre/tests/max_lines.rs`) in the `cargo test` gate — poly cannot count lines.
- When a file approaches the cap, refactor by extracting helpers, types, or submodules — never raise the cap.
- The codebase is file-per-module: a folder module gets a thin `mod.rs` that only declares submodules and re-exports; real logic lives in named sibling files (`detect/preprocess.rs`, `detect/postprocess.rs`, …). Match that shape when a module area grows.
