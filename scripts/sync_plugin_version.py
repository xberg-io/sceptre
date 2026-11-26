"""Sync the coding-agent plugin version to the core ``Cargo.toml`` version.

``ai-rulez generate --plugin`` renders every per-runtime plugin manifest under
``plugin/`` from ``plugin/.ai-rulez/config.toml``'s ``[plugin].version``. This script
keeps that single source, the MCP launcher's ``PINNED_VERSION``, the npm CLI proxy
manifest and ``server.json`` pinned to the crate version in ``Cargo.toml`` (the repo's
version source of truth). Run via ``mise run version:set`` (which then regenerates the
bundles); freshness of the generated bundles themselves is enforced by ``ai-rulez verify
--plugin`` in CI, so this script only touches the config source, the launcher pin and the
publish manifests.

Usage:
    python3 scripts/sync_plugin_version.py                 # apply
    python3 scripts/sync_plugin_version.py --check         # verify against Cargo.toml
    python3 scripts/sync_plugin_version.py --expect X.Y.Z  # verify every pin equals X.Y.Z

``--check`` answers "does plugin/ track core?" and is the gate CI runs on `main`.
``--expect`` additionally pins both to the version actually being released, so a
release cannot ship a plugin bundle that lags the tag it is built from. Both exit 1
on drift.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_CONFIG = ROOT / "plugin" / ".ai-rulez" / "config.plugins.toml"
if not PLUGIN_CONFIG.exists():
    PLUGIN_CONFIG = ROOT / "plugin" / ".ai-rulez" / "config.toml"
# ~keep Matches the `version` key of the `[plugin]` table only. The file also has a
# top-level ai-rulez schema `version = "4.0"` that must never be rewritten.
PLUGIN_VERSION_RE = re.compile(r'(\[plugin\][^\[]*?\nversion = ")([^"]*)(")', re.DOTALL)
LAUNCHER = ROOT / "plugin" / ".ai-rulez" / "scripts" / "mcp-launch.sh"
# ~keep The launcher pins the exact release it fetches and the minimum binary version it accepts,
# so it has to move with every release exactly like the plugin manifest does.
LAUNCHER_PIN_RE = re.compile(r'(?m)^(PINNED_VERSION=")([^"]*)(")')
NPM_MANIFEST = ROOT / "cli-proxy" / "npm" / "package.json"
SERVER_JSON = ROOT / "server.json"
# ~keep The CLI proxy publishes in lockstep with the product and server.json names that exact npm
# version for the MCP Registry, so both are pinned here rather than hand-edited. Each pattern keeps
# the surrounding JSON layout so a rewrite is a one-line diff.
NPM_VERSION_RE = re.compile(r'(?m)^(  "version": ")([^"]*)(")')
SERVER_VERSION_RES = (
    re.compile(r'(?m)^(  "version": ")([^"]*)(")'),
    re.compile(r'(?m)^(      "version": ")([^"]*)(")'),
)
SYNC_HINT = "run `python3 scripts/sync_plugin_version.py` and `ai-rulez generate --plugin`"


def read_pin(path: Path, pattern: re.Pattern[str], label: str) -> str:
    """Read the first capture of ``pattern`` from ``path``, exiting when it is absent."""
    match = pattern.search(path.read_text(encoding="utf-8"))
    if not match:
        sys.exit(f"could not read {label} from {path.relative_to(ROOT)}")
    return match.group(2)


def pins() -> dict[Path, list[tuple[re.Pattern[str], str]]]:
    """Every file the script rewrites, with the patterns and labels of its version pins."""
    return {
        LAUNCHER: [(LAUNCHER_PIN_RE, "PINNED_VERSION")],
        NPM_MANIFEST: [(NPM_VERSION_RE, "version")],
        SERVER_JSON: [(SERVER_VERSION_RES[0], "version"), (SERVER_VERSION_RES[1], "packages[0].version")],
    }


def current_pins() -> dict[str, str]:
    """Map each pin's label to the version it holds."""
    found: dict[str, str] = {}
    for path, patterns in pins().items():
        for pattern, label in patterns:
            found[f"{path.relative_to(ROOT)} {label}"] = read_pin(path, pattern, label)
    return found


def rewritten_pins(version: str) -> dict[Path, tuple[str, str]]:
    """Map each pinned file to its text before and after rewriting every pin to ``version``."""
    changes: dict[Path, tuple[str, str]] = {}
    for path, patterns in pins().items():
        original = path.read_text(encoding="utf-8")
        text = original
        for pattern, label in patterns:
            count = len(pattern.findall(text))
            if count < 1:
                sys.exit(f"{path.relative_to(ROOT)}: no {label} matched; the file shape changed. {SYNC_HINT}")
            text = pattern.sub(rf"\g<1>{version}\g<3>", text, count=1)
        changes[path] = (original, text)
    return changes


def core_version() -> str:
    """Read the workspace crate version from ``Cargo.toml``."""
    text = (ROOT / "Cargo.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"', text)
    if not match:
        sys.exit("could not read version from Cargo.toml")
    return match.group(1)


def plugin_version() -> str:
    """Read ``[plugin].version`` from the plugin config."""
    match = PLUGIN_VERSION_RE.search(PLUGIN_CONFIG.read_text(encoding="utf-8"))
    if not match:
        sys.exit(f"could not read [plugin].version from {PLUGIN_CONFIG.relative_to(ROOT)}")
    return match.group(2)


def transform(version: str) -> tuple[str, str]:
    """Rewrite ``version`` inside the ``[plugin]`` table (not the top-level ai-rulez
    schema ``version = "4.0"``) of the plugin config. Uses the native/semver form,
    which is also what ai-rulez expects; ai-rulez renders the PEP 440 form for the
    Hermes wheel.
    """
    original = PLUGIN_CONFIG.read_text(encoding="utf-8")
    # ~keep Assert the pattern matched something. ``main`` reads an unchanged file as
    # "already in sync", and a substitution that matched nothing produces exactly the same
    # unchanged file -- so if the ``[plugin]`` table is ever reshaped, ``--check`` would keep
    # passing while the plugin version silently stopped tracking core, and the release would
    # ship a plugin bundle pinned to whatever version was last written by hand. Fail here
    # instead. Do not replace this with an after-the-fact check that the file contains the
    # expected version: that is satisfied both by a successful rewrite and by a file that was
    # already correct for the wrong reason.
    updated, count = PLUGIN_VERSION_RE.subn(rf"\g<1>{version}\g<3>", original, count=1)
    if count != 1:
        sys.exit(
            f"{PLUGIN_CONFIG.relative_to(ROOT)}: no [plugin].version key matched — the config "
            f"shape changed and the plugin version is no longer being synced. {SYNC_HINT}"
        )
    return original, updated


def parse_expect(argv: list[str]) -> str | None:
    """Return the version passed to ``--expect``, or ``None`` when absent."""
    for index, arg in enumerate(argv):
        if arg == "--expect":
            if index + 1 >= len(argv):
                sys.exit("--expect requires a version argument")
            return argv[index + 1]
        if arg.startswith("--expect="):
            return arg.split("=", 1)[1]
    return None


def report_drift(expected: str, core: str, plugin: str, pinned: dict[str, str]) -> int:
    """Print every version that disagrees with ``expected`` and fail."""
    print(f"plugin/core version drift — expected {expected}")
    if core != expected:
        print(f"  Cargo.toml [package].version -> {core}")
    if plugin != expected:
        print(f"  {PLUGIN_CONFIG.relative_to(ROOT)} [plugin].version -> {plugin}")
    for label, found in pinned.items():
        if found != expected:
            print(f"  {label} -> {found}")
    print(SYNC_HINT)
    return 1


def main() -> int:
    argv = sys.argv[1:]
    expect = parse_expect(argv)
    core = core_version()

    if expect is not None:
        plugin = plugin_version()
        pinned = current_pins()
        if core == expect and plugin == expect and all(found == expect for found in pinned.values()):
            print(f"plugin, launcher, CLI proxy, server.json and core all at {expect}")
            return 0
        return report_drift(expect, core, plugin, pinned)

    original, updated = transform(core)
    changes = rewritten_pins(core)
    if original == updated and all(before == after for before, after in changes.values()):
        return 0
    if "--check" in argv:
        return report_drift(core, core, plugin_version(), current_pins())
    PLUGIN_CONFIG.write_text(updated, encoding="utf-8")
    for path, (_, after) in changes.items():
        path.write_text(after, encoding="utf-8")
    print(f"synced plugin version, launcher pin and publish manifests -> {core}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
