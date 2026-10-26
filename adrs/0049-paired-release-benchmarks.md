---
status: proposed
date: 2026-10-27

---

# Measure a published release and candidate on the same hosted machine

## Context and Problem Statement

PR #8 intentionally moved the CPU benchmark to `ubuntu-latest`, but retained the committed
`runner-medium` measurements. ADRs 0042 and 0043 correctly reject that incomparable baseline.
Returning to an unavailable private runner or changing its old measurements' host labels would
not qualify a release on the hosted infrastructure.

## Decision Outcome

Run the genuine published 0.8.1 executable and the final release candidate serially in the same
ready-main job, using the current harness. Bind the old executable to its official GitHub release
asset digest and regular archive member; record the independent candidate hash, source revision
and observed version. Retain both raw reports and a manifest with artifact hashes.

Verify every expected image, labeled ground truth and pinned model file before measurement, then
verify those bytes again afterwards. Explicit thread counts, configuration source defaults,
measured model identities, effective backend/accelerator, ONNX Runtime version/build identity and
host provenance must match. Unknown or mismatched runtime identity is a failure that requires
investigation; it must not be replaced with a uniform label. Configuration-source changes require
an explicit comparison design before this gate can accept them.

Convert the old binary's actual measured report into a local baseline with the existing publisher.
Preserve its observed 0.8.1 version. Apply the unchanged 0.90 throughput floor and 1.10 RSS ceiling
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
