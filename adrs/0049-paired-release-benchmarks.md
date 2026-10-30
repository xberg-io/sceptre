---
status: accepted
date: 2026-10-27
decision-makers: ["Na'aman Hirschfeld"]
amends: ["0042", "0043"]
---

# Measure a published release and candidate on the same hosted machine

## Context and Problem Statement

PR #8 intentionally moved the CPU benchmark to `ubuntu-latest`, but retained the committed
`runner-medium` measurements. ADRs 0042 and 0043 correctly reject that incomparable baseline.
Returning to an unavailable private runner or changing its old measurements' host labels would
not qualify a release on the hosted infrastructure.

## Considered Options

* Keep the committed `runner-medium` measurements as the baseline for the hosted `ubuntu-latest`
  benchmark (status quo, rejected by ADRs 0042 and 0043).
* Return to the unavailable private runner.
* Change the old measurements' host labels.
* Measure a published release and the candidate on the same hosted machine.

## Decision Outcome

Chosen option: "measure a published release and the candidate on the same hosted machine", because
returning to an unavailable private runner or changing its old measurements' host labels would not
qualify a release on the hosted infrastructure. Run the genuine published executable of the latest
qualified release, 0.8.2, and the final release candidate serially in the same ready-main job,
using the current harness. Pin that identity explicitly in the release harness. Bind the old
executable to its official GitHub release asset digest and regular archive member, and resolve its
immutable tag for the configuration-source comparison; record the independent candidate hash,
source revision and observed version. Retain both raw reports and a manifest with artifact hashes.

Verify every expected image, labeled ground truth and pinned model file before measurement, then
verify those bytes again afterwards. Explicit thread counts, configuration source defaults,
measured model identities, effective backend/accelerator, ONNX Runtime version/build identity and
host provenance must match. Unknown or mismatched runtime identity is a failure that requires
investigation; it must not be replaced with a uniform label. Configuration-source changes require
an explicit comparison design before this gate can accept them.

Convert the old binary's actual measured report into a local baseline with the existing publisher.
Preserve both independently observed executable versions, and reject a stale 0.8.1 baseline
before timing. Apply the unchanged 0.90 throughput floor and 1.10 RSS ceiling
to the candidate, and the existing baseline-derived per-image token-F1 contracts. Missing rows,
missing measurements, skipped ordinary images and empty quality contracts fail. Capability probes
retain their separate unsupported-format semantics.

The committed public benchmark artifact and generated documentation remain untouched until a
measured result is deliberately reviewed and published. A passing unit test qualifies harness
logic; only the real native two-executable run qualifies release performance and quality. Release
packaging, platform OCR, security, and publish ordering remain separate required gates.

This amends the source of the comparable host baseline in ADRs 0042 and 0043, retaining their
numeric thresholds and fail-closed semantics. Existing ordinary benchmark CLI defaults continue
to use the committed baseline; explicit binary and baseline selectors are additive.

The comparator was 0.8.1 until 2026-10-28, when the 0.9.0 candidate upgraded the public ONNX
Runtime Rust dependency and the comparator moved to 0.8.2 with every other requirement unchanged.
The historical 0.8.1-to-0.8.2 regression fixtures and shallow-checkout failure controls are
retained.
