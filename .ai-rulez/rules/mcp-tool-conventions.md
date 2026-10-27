---
type: Decision
title: Mcp Tool Conventions
paths:
  - "crates/sceptre/src/mcp/**"
  - "crates/sceptre/tests/mcp_smoke.rs"
x-ai-rulez:
  kind: rule
  id: mcp-tool-conventions
  metadata:
    priority: high
---

# MCP Tool Conventions

- The MCP surface lives in `crates/sceptre/src/mcp/`, behind the `mcp` cargo feature, and is exposed through the `sceptre mcp` subcommand.
- Adding or changing a tool touches, in order: `mcp/types.rs` (request/response schemas) → `mcp/tools.rs` (a `#[tool]` on the `#[tool_router]` impl; `server.rs` needs no change) → `tests/mcp_smoke.rs` → the README tool table, `docs-site/src/content/docs/guides/mcp-server.mdx` and `plugin/.ai-rulez/skills/sceptre-using-the-mcp-server/` (then `task plugin:generate`).
- Tool bodies are thin wrappers that build an `OcrConfig`/`Reader` and call the library; no OCR logic lives in the MCP layer.
- Optional parameters use `Option<T>` with `#[serde(default)]`; keep additions backward-compatible.
