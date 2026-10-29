---
type: Playbook
title: Sceptre Release
description: "Sceptre release on top of the shared release-workflow: version:set, CHANGELOG section, tag-driven publish order. Use when bumping the version or tagging."
x-ai-rulez:
  kind: skill
  id: sceptre-release
  metadata:
    name: sceptre-release
---

# Sceptre release

Repo specifics for the shared `release-workflow` skill.

- `mise run version:set X.Y.Z` sets the workspace and plugin versions and regenerates the plugin bundles. publish.yaml also fails unless `[workspace.dependencies].sceptre` in Cargo.toml equals the tag version: check that pin moved.
- CHANGELOG.md needs a `## [X.Y.Z]` section: publish.yaml uses it as the release notes and fails without it. Then run `mise run docs:changelog`.
- Pushing tag `vX.Y.Z` runs publish.yaml, which creates the draft release itself, then builds the platform archives and checksums, promotes the draft, and publishes `sceptre` then `sceptre-cli` to crates.io and the plugin artifacts. Do not `gh release create`.
- `mise run release:dry-run` cannot dry-run `sceptre-cli` until the matching `sceptre` is on crates.io; `scripts/dry-run-cli.sh` skips that case loudly.
- Before tagging run `mise run check` and `mise run rust:release:smoke:test`; main CI is not a release gate (ADR 0048).
