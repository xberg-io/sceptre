---
type: Decision
title: Rust Comments
paths:
  - "**/*.rs"
x-ai-rulez:
  kind: rule
  id: rust-comments
  metadata:
    priority: high
---

- Rust doc comments (`///`, `//!`) carry explanatory content and are kept without a `~keep` marker.
- No session numbers, milestone tags or progress notes ("Session 1", "M1", "wired later", "TODO next") in comments or
  `todo!()` messages: describe what the code does or what behavior is missing.
