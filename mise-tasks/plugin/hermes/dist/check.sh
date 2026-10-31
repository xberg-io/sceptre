#!/usr/bin/env bash
#MISE description="Build the Hermes plugin wheel and check its distribution metadata with twine"
set -euo pipefail
wheel_dir=$(mktemp -d)
[ -n "$wheel_dir" ] && [ -d "$wheel_dir" ]
uv build --wheel --out-dir "$wheel_dir" plugin/.hermes/package
wheels=("$wheel_dir"/*.whl)
[ "${#wheels[@]}" -eq 1 ] && [ -f "${wheels[0]}" ]
uvx --from twine==7.0.0 --with packaging==26.3 twine check --strict "${wheels[0]}"
