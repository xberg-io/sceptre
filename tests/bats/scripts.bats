#!/usr/bin/env bats

setup() {
  bats_load_library xberg-bats
  xberg_setup
  REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd -P)"
  mkdir -p "$XBERG_WORK/scripts" "$XBERG_WORK/docs-site/src/content/docs/more"
  cp "$REPO_ROOT"/scripts/*.sh "$XBERG_WORK/scripts/"
  printf 'version = "1.2.3"\n' >"$XBERG_WORK/Cargo.toml"
  cd "$XBERG_WORK" || return
}

@test "CLI dry run publishes only when the library version is available" {
  xberg_stub curl 'printf 200'
  xberg_stub_trace cargo
  run bash scripts/dry-run-cli.sh
  xberg_assert_status 0
  xberg_assert_trace 'cargo publish --dry-run -p sceptre-cli --no-default-features --features ort-dynamic,download'
}

@test "CLI dry run explains an unpublished library without invoking cargo" {
  xberg_stub curl 'printf 404'
  xberg_stub_trace cargo
  run bash scripts/dry-run-cli.sh
  xberg_assert_status 0
  xberg_assert_output_contains 'sceptre 1.2.3 is not on crates.io'
  xberg_assert_trace_empty
}

@test "CLI dry run does not treat registry failures as an unpublished version" {
  xberg_stub curl 'printf 403'
  xberg_stub_trace cargo
  run bash scripts/dry-run-cli.sh
  xberg_assert_status 1
  xberg_assert_output_contains 'HTTP 403'
  xberg_assert_trace_empty
}

@test "release packaging includes binary and emitted runtime library" {
  triple=aarch64-unknown-linux-gnu
  mkdir -p "target/$triple/release"
  printf 'binary fixture\n' >"target/$triple/release/sceptre"
  printf 'runtime fixture\n' >"target/$triple/release/libonnxruntime.so"
  run bash scripts/package-release.sh "$triple"
  xberg_assert_status 0
  mkdir unpacked
  tar -xzf "sceptre-$triple.tar.gz" -C unpacked
  xberg_assert_file unpacked/sceptre 'binary fixture'
  xberg_assert_file unpacked/libonnxruntime.so 'runtime fixture'
  [ ! -e "sceptre-staging-$triple" ]
}

@test "release packaging rejects unsupported targets and missing binaries" {
  run bash scripts/package-release.sh unsupported
  xberg_assert_status 1
  xberg_assert_output_contains 'Unknown target triple'
  run bash scripts/package-release.sh aarch64-unknown-linux-gnu
  xberg_assert_status 1
  xberg_assert_output_contains 'Binary not found'
}

@test "changelog sync renders docs links and detects stale output" {
  printf '# Changelog\n\n## [Unreleased]\n\nSee [ADR](adrs/example.md).\n' >CHANGELOG.md
  run bash scripts/sync-changelog.sh
  xberg_assert_status 0
  target=docs-site/src/content/docs/more/changelog.md
  grep -q '^title: "Changelog"$' "$target"
  grep -q 'https://github.com/xberg-io/sceptre/blob/main/adrs/example.md' "$target"
  run bash scripts/sync-changelog.sh --check
  xberg_assert_status 0
  printf '\nstale\n' >>"$target"
  run bash scripts/sync-changelog.sh --check
  xberg_assert_status 1
  xberg_assert_output_contains 'is stale'
}

@test "Python typecheck syncs locked dependencies before checking" {
  xberg_stub_trace uv
  run bash scripts/typecheck.sh
  xberg_assert_status 0
  xberg_assert_trace $'uv sync --locked --all-groups --no-build --no-install-project\nuv run --no-sync pyrefly check'
}

@test "Python typecheck stops after dependency synchronization fails" {
  xberg_stub uv 'printf "%s\n" "$*" >>"$XBERG_TRACE"; exit 31'
  run bash scripts/typecheck.sh
  xberg_assert_status 31
  xberg_assert_trace 'sync --locked --all-groups --no-build --no-install-project'
}

feature_graph() {
  xberg_stub cargo 'printf "%s\n" "$*" >>"$XBERG_TRACE"
features="default"
while [ "$#" -gt 0 ]; do
  if [ "$1" = --features ]; then shift; features="$1"; fi
  shift
done
printf "sceptre v1.2.3|download,mcp\n"
case "$features" in
  tract,download|candle,download) ;;
  ort-dynamic) printf "ort v2.0.0|load-dynamic\n" ;;
  candle-metal) printf "candle-core v0.11.0|metal\n" ;;
  candle-cuda) printf "candle-core v0.11.0|cuda\n" ;;
  ort-coreml) printf "ort v2.0.0|download-binaries,coreml\n" ;;
  ort-directml) printf "ort v2.0.0|download-binaries,directml\n" ;;
  ort-cuda) printf "ort v2.0.0|download-binaries,cuda\n" ;;
  *) printf "ort v2.0.0|download-binaries\n" ;;
esac'
}

@test "feature verification checks all thirteen resolution cases without compiling" {
  feature_graph
  run bash scripts/verify-features.sh
  xberg_assert_status 0
  xberg_assert_output_contains 'All feature-resolution expectations hold'
  [ "$(wc -l <"$XBERG_TRACE" | tr -d ' ')" -eq 13 ]
}

@test "feature verification refuses failed cargo resolution for every case" {
  xberg_stub cargo 'printf "resolution fixture failed\n" >&2; exit 42'
  run bash scripts/verify-features.sh
  xberg_assert_status 1
  xberg_assert_output_contains 'did not resolve'
  xberg_assert_output_contains '13 feature-resolution expectation(s) failed'
}

@test "shared helper sync rejects mutable refs and detects drift" {
  xberg_stub_curl_file "$REPO_ROOT/tests/lib/xberg-bats/load.bash"
  export BATS_LIB_DEST="$XBERG_WORK/lib" BATS_LIB_REF=main
  run bash scripts/sync-bats-lib.sh sync
  xberg_assert_status 1
  export BATS_LIB_REF=v1.29.0
  run bash scripts/sync-bats-lib.sh sync
  xberg_assert_status 0
  run bash scripts/sync-bats-lib.sh --check
  xberg_assert_status 0
  printf '\nchanged\n' >>"$BATS_LIB_DEST/load.bash"
  run bash scripts/sync-bats-lib.sh --check
  xberg_assert_status 1
  xberg_assert_output_contains 'has drifted'
}
