---
type: Concept
title: Area Map
x-ai-rulez:
  kind: context
  id: area-map
  metadata:
    priority: high
---

# Area Map

sceptre is a Rust OCR library, CLI and MCP server reimplementing EasyOCR over ONNX.

- `crates/sceptre/` — core library (`crate-layout`, `backend-seam` rules)
- `crates/sceptre/src/{detect,recognize,models}/` — detection, recognition, model provisioning (`ocr-pipeline` rule)
- `crates/sceptre/src/mcp/` — MCP server (`mcp-tool-conventions` rule)
- `crates/sceptre-cli/` — command-line binary
- `python/sceptre_rs_tools/` — primary model export (`mise run python:export`, ADR 0025), EasyOCR golden half (`mise run python:golden`), benchmark harness
- `tools/` — `sceptre-tools` dev crate: sceptre golden half (`snapshot`); its export subcommand is unimplemented
- `benchmarks/published/` — committed benchmark artifact
- the corpus submodule (see `.gitmodules`) — `mise run setup` fetches its `images/**` by sha256 (`adrs/0034`)
- `adrs/` — architecture decision records (`adr-discipline` rule)
- `docs-site/`, `docs/` — docs site and assets
- `skills/`, `plugin/` — published skills, agent plugin, generated from `plugin/.ai-rulez/` (`generated-artifacts` rule)
- `scripts/` — release and verification scripts
- CI runs only on main (ADR 0048): a PR gets no build or test checks. Before calling one ready run `mise run check` and `mise run lint`, plus as touched `mise run python:test`, `mise run plugin:verify`, `mise run docs:changelog:check`, `mise run python:publish:check`.
