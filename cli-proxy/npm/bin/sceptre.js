#!/usr/bin/env node
// Launcher: exec the native sceptre binary, forwarding argv and inheriting stdio. ~keep
// Order: the binary shipped by the installed platform package (no network), then a healthy ~keep
// binary already in bin/, then an on-demand download from the GitHub release. ~keep
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { resolveBundledBinary } from "../install.js";

const BIN_NAME = "sceptre";

function binaryName() {
  return os.type() === "Windows_NT" ? `${BIN_NAME}.exe` : BIN_NAME;
}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// install.js extracts the binary into this same bin/ directory. ~keep
const binPath = path.join(__dirname, binaryName());

// A cached binary is only usable if it is non-empty and (on non-Windows) has an ~keep
// exec bit. A truncated or non-executable file means a corrupt cache: re-download. ~keep
function isHealthy(file) {
  try {
    const stat = fs.statSync(file);
    if (stat.size <= 0) return false;
    if (os.type() !== "Windows_NT" && (stat.mode & 0o111) === 0) return false;
    return true;
  } catch {
    return false;
  }
}

// npm packs files outside `bin` fields without an exec bit on some versions, so restore it. ~keep
function ensureExecutable(file) {
  if (os.type() === "Windows_NT") return;
  try {
    const { mode } = fs.statSync(file);
    if ((mode & 0o111) === 0) fs.chmodSync(file, mode | 0o755);
  } catch {}
}

async function ensureBinary() {
  if (fs.existsSync(binPath) && isHealthy(binPath)) return;
  process.stderr.write(`${BIN_NAME}: binary missing or corrupt, attempting download...\n`);
  // Call main() explicitly rather than relying on import side-effects: ESM ~keep
  // caches modules, so the installer's top-level run is gated to direct ~keep
  // invocation only and would not fire on import. ~keep
  const { main: runInstaller } = await import("../install.js");
  await runInstaller();
}

function printUnavailable() {
  process.stderr.write(
    `${BIN_NAME} is not available for your platform yet. Install it with:\n` +
      `  cargo install sceptre-cli --locked --features mcp\n` +
      `  or download a release archive: https://github.com/xberg-io/sceptre/releases\n`,
  );
}

async function main() {
  const bundled = resolveBundledBinary();
  if (bundled) ensureExecutable(bundled);
  const target = bundled && isHealthy(bundled) ? bundled : null;
  if (!target) {
    await ensureBinary();
    if (!fs.existsSync(binPath) || !isHealthy(binPath)) {
      printUnavailable();
      process.exit(1);
    }
  }
  const result = spawnSync(target ?? binPath, process.argv.slice(2), { stdio: "inherit" });
  if (result.error) {
    process.stderr.write(`${BIN_NAME}: failed to spawn binary: ${result.error.message}\n`);
    process.exit(1);
  }
  process.exit(result.status ?? 0);
}

main().catch((err) => {
  // No standalone CLI for this platform: print the graceful install hint, not a stack. ~keep
  if (err && err.name === "CliUnavailableError") {
    process.stderr.write(`${BIN_NAME}: ${err.message}\n`);
    printUnavailable();
    process.exit(1);
  }
  process.stderr.write(`${BIN_NAME}: ${err.message}\n`);
  process.exit(1);
});
