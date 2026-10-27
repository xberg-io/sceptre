---
type: Decision
title: Crate Layout
paths:
  - "crates/**"
  - "Cargo.toml"
x-ai-rulez:
  kind: rule
  id: crate-layout
  metadata:
    priority: high
---

# Crate Layout

A Cargo workspace: an rlib core, a thin CLI, and the dev-only `tools/` crate (not a default member). Shared metadata, dependency pins, lints, and profiles live in the root `Cargo.toml`; members inherit with `.workspace = true`.

## `crates/sceptre` (library)

- `lib.rs` — crate docs, module declarations, flat re-exports; `error.rs` — `OcrError` + `Result`; `types.rs` — result and geometry types.
- `config/` — per-stage config structs aggregated in `OcrConfig`.
- `engine/` — `Reader` + `ReaderBuilder`, the `OcrEngine` seam with `SceptreEngine` and `FallbackEngine`; `engine/seams/` holds the injectable `ModelProvider` / `ProgressSink` traits.
- `imaging.rs` — decode to RGB + grayscale.
- `detect/` — CRAFT detection, the orientation pre-pass, box geometry and line grouping.
- `recognize/` — cropping, CRNN, CTC greedy and beam decoding, charsets.
- `inference/` — `ModelBackend` seam, `ort` / `tract` backends, `ort` execution providers, runtime provenance, and `candle/` hand-written networks.
- `models/` — gen2 model registry, download, integrity checks, provisioning.
- `mcp/` — rmcp server (`mcp` feature); `bench.rs` — hidden bench seam (`bench` feature).

## `crates/sceptre-cli` (binary `sceptre`)

- `main.rs` (thin), `cli.rs` (clap + dispatch), `overrides.rs` (flags → `OcrConfig`), `output.rs` (text/JSON rendering), `timing.rs` (`--timings`), `style.rs` (anstyle palette).

Root config: `poly.toml`, `rustfmt.toml`, `deny.toml`, `Taskfile.yaml` + `.task/`.
