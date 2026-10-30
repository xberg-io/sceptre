---
status: accepted
date: 2026-10-28
decision-makers: ["Na'aman Hirschfeld"]
amends: ["0020", "0031"]
---

# GitHub Actions on major-tag pins and macOS runners on macos-26

## Context and Problem Statement

The workflows pinned some actions to commit SHAs and others to exact version tags, and macOS legs
ran on the floating `macos-latest` label, which [ADR 0020](0020-release-strategy.md)'s release
matrix and [ADR 0031](0031-hand-written-candle-networks.md)'s measurements name. GitHub deprecated
the macOS 14 image, so `macos-latest` and the `macos-15` release verifier would move under the
workflows without a change in this repository.

## Decision Drivers

* Action references follow one pinning rule across the organization.
* Every macOS leg runs on a runner label that does not move under it.

## Considered Options

* Keep the mix of SHA pins, exact version tags and `macos-latest` (status quo).
* Pin every action to its major tag and pin macOS legs to `macos-26`.

## Decision Outcome

Chosen option: "pin every action to its major tag and pin macOS legs to `macos-26`", because
action references then follow one rule across the organization, and macOS legs stop moving with
GitHub's deprecation of older images.

* Every `uses:` reference is on its major tag (`@v1`, `@v7`, ...). Each SHA resolved to a release in
  the same major, so inputs did not change (3fd5cba, 2026-10-27; 4252fec, 2026-10-27). An action that
  publishes no bare major tag stays on the exact tag of the same commit (`Jimver/cuda-toolkit`).
* Every macOS leg is Apple silicon and runs on `macos-26`, replacing `macos-latest` and the
  `macos-15` release verifier (39e3bad, 2026-10-28). The same commit updated ADR 0035's runner
  assignment in place; this ADR is the record of that change.

The organization-wide rules are org ADR "GitHub Actions pinned to major tags" and org ADR "macOS
runners on macos-26 and macos-26-intel" (agent-conventions `adrs/`). This ADR records how sceptre
applies them.

This amends ADR 0020's release matrix, which ADR 0023 already superseded, and ADR 0031: its
`macos-latest` figures remain historical measurements, and new macOS measurements run on `macos-26`.

### Consequences

* Good, because a new release within a major reaches every workflow without a pin change.
* Good, because macOS results are attributable to one fixed runner image.
* Bad, because a major-tag pin trusts the action's maintainers not to break a major; a SHA pin
  would not.

### Confirmation

`grep -rn 'uses:' .github/workflows` shows only major tags, apart from the documented exception,
and `grep -rn 'macos-' .github/workflows` shows only `macos-26`. Workflow changes are reviewed
against this ADR; no CI gate enforces it in this repository.
