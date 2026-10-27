---
type: Decision
title: Code Style
paths:
  - "crates/**/*.rs"
x-ai-rulez:
  kind: rule
  id: code-style
  metadata:
    priority: high
---

# Code Style

## Surface

- The library re-exports a curated flat surface from `lib.rs` (`pub use error::{OcrError, Result}`, `pub use types::*`, the config types), so consumers write `use sceptre::{Reader, OcrConfig, OcrResult}`.

## Errors

- Library errors: one `thiserror` enum (`OcrError`) plus `pub type Result<T>`. System errors (`Io`) bubble via `#[from]`; application variants carry `message` + an optional `#[source]`.
- CLI errors: `anyhow` with `.with_context(...)`.

## Config

- Aggregate struct (`OcrConfig`) of per-stage structs, each `#[serde(deny_unknown_fields)]` + `#[serde(default)]` with a `Default` impl. Precedence: defaults < file < env < flags.

## Dependency injection

- Extension points are traits with in-crate default impls stored as `Arc<dyn Trait>` "seams" on the `Reader`, built via `Reader::builder()`. No global mutable state.

## Output & concurrency

- `tracing` → stderr; structured data → stdout. Raw `print_stdout`/`print_stderr` are denied workspace-wide; the CLI passes `anstream::stdout()` as the writer to `output::render_*`, so never add `println!`/`eprintln!`.
- Terminal colour uses `anstyle` rendered through `anstream` (honors `NO_COLOR`).
- Parallelism is Rayon `par_iter` bounded by the single `ConcurrencyConfig` budget.
