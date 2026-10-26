#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[ -n "$repo_root" ] || exit 1
cd "$repo_root"
uv sync --locked --all-groups --no-build --no-install-project
uv run --no-sync pyrefly check
