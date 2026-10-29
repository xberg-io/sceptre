#!/usr/bin/env bash
#MISE description="Compare genuine published and candidate executables on one host with unchanged release gates"
#USAGE flag "--binary <path>" default="target/release/sceptre" help="Candidate sceptre executable"
#USAGE flag "--threads <n>" default="2" help="Worker threads for both releases"
#USAGE flag "--output <dir>" default="benchmark-results/release" help="Report directory"
#USAGE arg "[args]..." var=#true help="Extra arguments for sceptre_rs_tools.release_benchmark"
# shellcheck disable=SC2154 # usage_* are set by mise from the #USAGE lines
set -euo pipefail

# mise passes the variadic arg as one shell-quoted string; eval restores the original words. ~keep
eval "extra=(${usage_args:-})"
uv run python -m sceptre_rs_tools.release_benchmark --candidate-binary "$usage_binary" \
	--threads "$usage_threads" --output "$usage_output" ${extra[@]+"${extra[@]}"}
