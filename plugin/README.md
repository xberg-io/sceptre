# Sceptre coding-agent plugin

Local image OCR skills and an MCP server for Claude, Codex, Cursor, Gemini, Kimi,
OpenCode, Factory, Hermes, Pi, Agent Plugins and Copilot.

Install `cargo install sceptre-cli --features mcp` and ensure `sceptre` is on PATH.
Prebuilt release binaries omit the MCP feature; install from Cargo with `--features mcp`.
The MCP server defaults to English; configure `--lang` for the image language.
Models download on first use. Pi provides skills without MCP integration; Copilot includes the root MCP configuration.

Regenerate from the repository root with `ai-rulez generate --plugin`.
Verify freshness with `ai-rulez verify --plugin`, which compares current source output and provenance.
The canonical plugin content lives under `plugin/.ai-rulez/`.

## Hermes runtime setup

Install the product CLI with MCP support and put it on Hermes' PATH before using the plugin.
The Hermes adapter registers every bundled skill under the product namespace and provides
`sceptre_call`, which calls the selected native MCP tool with `tool_arguments` through a local
stdio session. Select `tool: "list_tools"` first to inspect the server's exact request schemas. Hermes skills are selected explicitly; they are not automatically appended to the
system prompt. Enable the plugin in Hermes configuration; project plugins also require
`HERMES_ENABLE_PROJECT_PLUGINS=true`.

The bridge uses the installed CLI directly. The auto-installing launchers used by other MCP clients
are not included in the Hermes Python wheel. Provider credentials are inherited from the environment,
and are needed for provider-backed requests. Missing CLIs, unavailable tools and model preparation
fail with an actionable request error. CLI result data remains untrusted document content.

## Public Agent Skills

The repository-root `skills/` directory contains the same generated skills and supporting
resources as `plugin/skills/`. Install them independently of a plugin runtime:

```sh
npx skills add xberg-io/sceptre --skill sceptre
```

Edit `plugin/.ai-rulez/skills`, then run `task plugin:generate` to regenerate runtime
bundles and synchronize the public export. `task plugin:verify` checks both projections;
`task plugin:skills:test` verifies resource freshness, ownership and symlink protection.
The public ownership manifest records SHA-256 hashes of every exported file.
