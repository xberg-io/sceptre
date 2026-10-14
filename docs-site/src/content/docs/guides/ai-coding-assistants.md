---
title: AI Coding Assistants
description: Install the sceptre coding-agent plugin or its standalone public skills.
---

The sceptre plugin bundles product instructions, runtime adapters and local tool access.

## Installing

For Claude Code:

```text
/plugin marketplace add xberg-io/sceptre
/plugin install sceptre@sceptre
```

For Codex, add `https://github.com/xberg-io/sceptre` through `/plugins`, then select the
sceptre plugin. For the other runtimes, follow [the plugin guide](https://github.com/xberg-io/sceptre/blob/main/plugin/README.md).

## Runtime resources and prerequisites

The generated bundle targets Claude Code, Codex, Cursor, Gemini CLI, Kimi, OpenCode,
Factory Droid, Hermes, Pi, Agent Plugins and GitHub Copilot CLI. Use
[the plugin installation guide](https://github.com/xberg-io/sceptre/blob/main/plugin/README.md)
for the runtime's installation method and configuration.

| Runtime | Integration |
| --- | --- |
| Claude, Codex, Cursor, Factory | Native plugin manifests, skills and MCP configuration |
| Gemini CLI | Extension manifest, command templates and MCP configuration |
| Kimi | Plugin manifest and session instructions |
| OpenCode | npm adapter, instructions and MCP configuration |
| Hermes | Python plugin, explicitly selected skills and a local stdio MCP bridge |
| Pi | Skills and prompt templates; execute operations through the CLI |
| Agent Plugins, Copilot | Agent Plugins 1.0 manifest, skills and MCP configuration |

Install the product CLI before using Hermes or Pi. Hermes starts the installed CLI directly;
its wheel does not include the auto-installing launcher used by other MCP clients.
Select `list_tools` through the product's Hermes bridge to inspect the supported tools and
request schemas. Select skills explicitly when needed; they are not appended automatically
to every conversation.

From a checkout, install the generated Hermes package into Hermes' Python environment:

```sh
pip install ./plugin/.hermes/package
```

Enable the plugin in Hermes configuration. Loading project plugins also requires
`HERMES_ENABLE_PROJECT_PLUGINS=true`. After a release publishes the updated package, the
registry install is `pip install sceptre-hermes-plugin`.

Pi resources can be installed from the checkout with `pi install ./plugin`.
After a plugin release includes them, install `npm:@xberg-io/opencode-sceptre` through Pi.
Pi does not register an MCP server, hooks or executable extensions from this package.

## Standalone public skills

The [public skills directory](https://github.com/xberg-io/sceptre/tree/main/skills) contains
instructions you can install independently of the runtime plugin. Use the
[skills CLI](https://github.com/vercel-labs/skills) to list and select them:

```sh
npx skills add xberg-io/sceptre --list
npx skills add xberg-io/sceptre
```

Choose the target agents interactively. For a local checkout, use `npx skills add ./skills`.
This installs instructions; it does not install the product CLI, enable MCP, download models
or set provider credentials.

For an MCP-enabled Cargo install, run `cargo install sceptre-cli --features mcp`.

OCR models download on first use. The MCP default language is English; configure it for the input.
