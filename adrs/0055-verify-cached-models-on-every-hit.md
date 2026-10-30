---
status: accepted
date: 2026-10-09
decision-makers: ["Na'aman Hirschfeld"]
amends: ["0017", "0054"]
---

# Verify cached models on every cache hit

## Context and Problem Statement

[ADR 0054](0054-resolve-cached-models-offline-first.md) resolves cached models offline first and
trusted a cached artifact because its sha256 had been verified at download time. A cached copy
that was corrupted or replaced after download was then served unchecked, and a lookup that did
not pin the revision could return a different snapshot than the registry names.

## Decision Drivers

* Only sha256-verified model bytes may be served.
* A cache hit resolves the registry's pinned revision, not whatever snapshot is present.
* Offline callers fail closed instead of serving unverified bytes.

## Considered Options

* Keep trusting cached bytes verified at download time (ADR 0054 as decided).
* Resolve the pinned revision and re-verify every cache hit, evicting a corrupt artifact.

## Decision Outcome

Chosen option: "resolve the pinned revision and re-verify every cache hit, evicting a corrupt
artifact", because only sha256-verified model bytes may be served.

* Every registry entry pins an immutable `revision`, and `resolve_cached` looks only in that
  revision's snapshot (cf090c1, 2026-10-09).
* A cache hit is sha256-verified before use; a corrupt artifact and its backing blob are evicted
  and fetched again (cf090c1, 28a2399, 2026-10-09).
* With `HF_HUB_OFFLINE` or `HUGGINGFACE_HUB_OFFLINE` set, a missing or corrupt artifact is an
  error rather than a download (b54775e, 2026-10-09).

Offline-first resolution from ADR 0054 is unchanged: a verified cache hit still needs no network.

### Consequences

* Good, because a corrupted or replaced cached artifact can no longer be served.
* Good, because the bytes in use always match the registry's pinned revision and sha256.
* Bad, because every cache hit re-hashes the model file.

### Confirmation

`ensure_with_env` in `crates/sceptre/src/models/download.rs` calls `verify_or_evict` on every
cache hit, with `hub_offline` deciding whether a miss may download. The unit tests
`resolve_cached_only_uses_the_requested_revision` and
`verify_or_evict_removes_a_corrupt_artifact_and_leaves_the_cache_a_miss`, and
`crates/sceptre/tests/model_bytes.rs` (`should_pin_builtin_models_to_immutable_revisions`,
`should_serve_only_sha256_verified_model_bytes`) cover it.
