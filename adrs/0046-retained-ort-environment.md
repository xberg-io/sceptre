---
status: accepted
date: 2026-10-14
decision-makers: ["Na'aman Hirschfeld"]
---

# Retain one ONNX Runtime environment per process

## Context and Problem Statement

`ort` 2.0.0-rc.14 requires an explicit `Environment` when constructing a session.
Its environment builder permits only one successful initialization per process,
including after the original environment has been dropped. Constructing an environment
for each model therefore loads the detector but fails when loading the recognizer.
A runtime-information probe can also consume the single initialization before OCR runs.

## Considered Options

* Construct an environment for each session. This fails on the second initialization.
* Thread an environment through every reader and runtime-information API. Independent
  readers still require coordination because the restriction applies to the process.
* Retain one immutable, fallibly initialized environment inside the ort backend.

## Decision Outcome

Chosen option: "retain one environment in a synchronized initialization cell and use it
for model sessions and runtime probes", because ort's environment builder permits only one
successful initialization per process, including after the original environment has been
dropped. Keep the helper internal to `inference`, gated by the
ort feature. Initialization failures retain their operation context and can be retried.
Session execution and accelerator registration remain per session, and concurrency
continues to use the existing `ConcurrencyConfig` budget.

This adds process-lifetime ownership of the native environment without changing public
configuration or introducing a library-installed tracing subscriber. It also means
applications must coordinate any independent use of ort's environment builder with
Sceptre; upstream does not expose a public accessor for an environment initialized elsewhere.

Pin ort to this exact prerelease. A compatible Cargo prerelease range can select a later
release candidate even when that candidate changes APIs, as rc.14 did to session builders
and execution providers. Upgrade subsequent candidates explicitly and repeat these checks.

## Validation

Exercise runtime probing followed by repeated model loading in one process, and run the
real detector/recognizer pipeline. A compile-only or single-session check cannot detect
the repeated-initialization failure.
