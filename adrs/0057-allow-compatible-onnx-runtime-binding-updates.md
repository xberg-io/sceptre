---
status: accepted
date: 2026-10-31
decision-makers: ["Na'aman Hirschfeld"]
amends: ["0046"]
---

# Allow compatible ONNX Runtime binding updates

## Context and Problem Statement

ADR 0046 retained a single ONNX Runtime environment and required an exact `ort`
prerelease because earlier candidates changed Rust APIs. The dependency refresh now
requires removing avoidable exact pins while using the latest published bindings.
The latest published `ort` and `ort-sys` releases are both `2.0.0-rc.15`.

## Considered Options

* Keep the exact `=2.0.0-rc.15` requirement.
* Allow Cargo's compatible range from `2.0.0-rc.15`, with the tested resolution locked.

## Decision Outcome

Chosen option: "allow Cargo's compatible range from `2.0.0-rc.15`, with the tested
resolution locked", because it permits dependency updates without an unnecessary
manifest edit while release builds remain reproducible through `Cargo.lock`.
This amends only ADR 0046's exact-version requirement. Its environment ownership,
fallible initialization, session construction and accelerator behavior remain unchanged.

### Consequences

* Good, because consumers can resolve a later compatible candidate or stable release
  without Sceptre blocking it through an exact prerelease requirement.
* Bad, because prerelease APIs can change despite satisfying Cargo's range; an unlocked
  consumer resolution may need adaptation before the next Sceptre release.

### Confirmation

`Cargo.toml` requires `ort = "2.0.0-rc.15"` without an equality operator, and
`Cargo.lock` records the tested `ort` and `ort-sys` versions. The existing
`inference::ort_backend::tests` cover tensor conversion and malformed output rejection.
Run the existing ignored `load_and_run_over_real_model` regression with ONNX Runtime
and a detector model when upgrading the resolved bindings; it probes the environment
before loading repeated sessions and running dynamic-width inputs.
