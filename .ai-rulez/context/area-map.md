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
- `tools/` — Rust model export and conversion
- `python/` — fallback model export, golden fixtures, benchmark harness
- `benchmarks/published/` — committed benchmark artifact
- the corpus submodule (see `.gitmodules`) — `task setup` fetches its `images/**` by sha256 (`adrs/0034`)
- `adrs/` — architecture decision records (`adr-discipline` rule)
- `docs-site/`, `docs/` — docs site and assets
- `skills/`, `plugin/` — published skills, agent plugin
- `scripts/` — release and verification scripts
