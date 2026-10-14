// AI-RULEZ :: GENERATED FILE — DO NOT EDIT
// Content-Hash: blake3:83493c5a39a83dc5711e794ce9df1b964d0f75ed3fd063ee5638a626c4de5f18
// Source-Hash: blake3:37ae8027dbd4b33d66846ad9bbe13ca51138e442fc1d8ab21d26ab06f0fe6f44
// Schema-Version: v1

/**
 * OpenCode v2 adapter for sceptre.
 *
 * To add OpenCode-specific tools or hooks:
 *
 * 1. Create .ai-rulez/opencode/index.js.
 * 2. Default-export { id, setup(ctx) } from that source file. OpenCode v2 does not
 *    run v1 plugins (an exported function returning hooks).
 * 3. If the plugin bundles skills, commands, or agents, call
 *    registerBundledContent(ctx) from ../ai-rulez-content.js in setup.
 * 4. Run ai-rulez generate --plugin --dry-run, then ai-rulez generate --plugin.
 *
 * Keep shared skills, commands, agents, and MCP configuration in their normal
 * .ai-rulez sources. Validate all external input and never interpolate untrusted
 * values into shell commands.
 */
import { registerBundledContent } from "../ai-rulez-content.js"

/** @type {import("@opencode/plugin").Plugin.Plugin} */
export default {
  id: "sceptre",
  async setup(ctx) {
    await registerBundledContent(ctx)
  },
}
