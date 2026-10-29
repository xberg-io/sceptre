#!/usr/bin/env bash
#MISE description="Set the workspace and plugin versions, then regenerate plugin bundles"
#USAGE arg "<version>" help="Release version, X.Y.Z"
# shellcheck disable=SC2154 # usage_* are set by mise from the #USAGE lines
set -euo pipefail

cargo set-version --workspace "$usage_version"
python3 scripts/sync_plugin_version.py
mise run plugin:generate
python3 scripts/sync_plugin_version.py --check
