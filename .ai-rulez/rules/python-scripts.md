---
type: Decision
title: Python Scripts
paths:
  - "scripts/**/*.py"
x-ai-rulez:
  kind: rule
  id: python-scripts
  metadata:
    priority: high
---

# Python Scripts

- `scripts/` Python imports only the stdlib and runs as `python3 scripts/…` outside the uv env; `test_hermes_plugin.py` gets its deps from `uv run --no-project --with`.
- `scripts/tests/` modules are `unittest` test cases ending in `if __name__ == "__main__": unittest.main()`, run by a task such as `release:smoke:test` or `plugin:skills:test`. pytest collects only `python/tests`, so a function-style test here never runs.
