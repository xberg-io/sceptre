---
status: accepted
date: 2026-10-29
decision-makers: ["Na'aman Hirschfeld"]
amends: ["0007", "0008", "0015", "0020", "0023", "0030", "0034", "0044"]
---

# mise tasks and the toolchain baseline

## Context and Problem Statement

[ADR 0007](0007-tooling-scaffolding-from-basemind.md) and [ADR 0008](0008-uv-taskfile-tools-infra.md)
made go-task (`Taskfile.yaml`, `.task/*.yml`) the task runner and left tool installation to each
contributor. [ADR 0015](0015-bench-seam-and-criterion.md) names a `task bench` target and
[ADR 0044](0044-single-ci-check-workflow.md) path-filters CI on `Taskfile.yaml` and `.task/**`.
The xberg-io organization has since moved every repository to mise, for tool versions first and then
for tasks, so sceptre needed one way to pin tools and one way to run tasks that matches the rest of
the organization.

## Decision Drivers

* One toolchain manager and one task runner across the organization, with no second tool to install.
* Tool versions pinned and locked with checksums for every platform CI runs on.
* CI calls the same tasks contributors run locally.

## Considered Options

* Keep go-task for tasks, with tools installed per contributor (status quo).
* Pin tools with mise but keep go-task for tasks.
* Pin tools and run tasks with mise, on the organization's toolchain baseline.

## Decision Outcome

Chosen option: "pin tools and run tasks with mise, on the organization's toolchain baseline",
because it gives one toolchain manager and one task runner that match the rest of the organization,
and CI then calls the same tasks contributors run locally.

* `mise.toml` pins every non-Rust tool at the `xberg-io/toolchains` baseline named in
  `toolchains.toml`, and `mise.lock` records checksums for linux-x64, linux-arm64, macos-arm64 and
  windows-x64 (86f23c9, 2026-10-28). Rust stays pinned by `rust-toolchain.toml`.
* `Taskfile.yaml` and `.task/` are replaced by mise tasks under the same names: one-liners in
  `mise.toml`, longer bodies as file tasks under `mise-tasks/`, and shared task sets from the
  toolchains library in `mise-tasks/shared.toml` (f6497c2, 2026-10-29).
* CI calls `mise run` instead of `task`, and its path filters watch `mise-tasks/` instead of
  `Taskfile.yaml` and `.task/` (36580cd, 2026-10-29).
* `bench`, `release:build` and `python:export` are removed; the benchmarks workflow runs
  `cargo bench` itself (34b9802, 2026-10-30).

The organization-wide decisions are recorded once, in agent-conventions: org ADR "mise toolchain
baseline" and org ADR "go-task to mise tasks and shared task sets" (agent-conventions `adrs/`).
This ADR records only how sceptre applies them.

This amends ADRs 0007, 0008, 0015 and 0044: read every `task <name>` and `Taskfile` setup target
in them as the mise task of the same name, and ADR 0015's `task bench` as `cargo bench -p sceptre
--features bench`. ADRs 0020, 0023, 0030 and 0034 also name `task` commands; the same reading
applies.

### Consequences

* Good, because contributors install one tool, and `mise install` provisions the rest at locked
  versions.
* Good, because CI and local runs share task definitions, and the shared task sets come from the
  toolchains library instead of being copied.
* Bad, because moving to a new baseline is a deliberate change to `toolchains.toml`, `mise.toml`
  and `mise.lock` together.

### Confirmation

The `toolchain` job in `.github/workflows/ci.yaml` runs `xberg-io/actions/check-toolchain@v1`,
which fails when `mise.toml` drifts from the baseline in `toolchains.toml`. The repository has no
`Taskfile.yaml` or `.task/` directory, and no workflow calls `task`.
