---
type: Reference
title: Check
description: Run the full lint + test gate before a release or a pipeline change
x-ai-rulez:
  kind: command
  id: check
  metadata:
    priority: high
    aliases:
      - c
    usage: /check
---

# Check

Run the full gate before a release, when the change touches the pipeline, or when asked. It is not a per-commit
step: per-commit checks are `poly lint .` and `poly fmt --check .`.

1. `task check` — `cargo fmt --all --check`, clippy `-D warnings`, the feature-matrix gate, workspace tests, `poly lint .`
2. `task python:lint` and `task python:test`

On failure:

- fmt — run `task format`, then re-stage.
- clippy — fix, or justify with a one-line `//` comment ending in `~keep`.
- tests — diagnose the failure; never `#[ignore]` to bypass.
- poly — fix the reported typo / markdown / deny / uncomment (`~keep`) issue.
