---
status: accepted
date: 2026-08-01
decision-makers: ["Na'aman Hirschfeld"]
amends: ["0017"]
---

# Resolve cached models offline first

## Context and Problem Statement

[ADR 0017](0017-hf-hub-native-cache.md) routes every model download through `hf-hub`'s
`download_file().send()`. That call revalidated the artifact against the Hub on every run, even
when it was already cached: a `304` round-trip that cost ~0.4–0.5 s of network latency per CLI
invocation and made every run depend on the network (be705e9).

## Decision Drivers

* A cached model must load without a network round-trip, so the CLI works fully offline.
* Cold-run latency should not pay for a Hub revalidation that returns "unchanged".

## Considered Options

* Keep revalidating every cached artifact against the Hub on each run (status quo from ADR 0017).
* Resolve from the local hub cache first and build the Hub client only on a miss.

## Decision Outcome

Chosen option: "resolve from the local hub cache first and build the Hub client only on a miss",
because a cached model then loads without a network round-trip and the CLI works fully offline.
`ensure` returns the cached snapshot path when the artifact resolves in the hub cache and fetches
only on a miss (be705e9, 2026-08-01); cold `sceptre run` dropped from ~0.95 s to ~0.47 s.

As decided, a cache hit trusted the bytes that were sha256-verified at download time and did not
re-hash them on every run; a machine holding an old cached copy kept serving it until the snapshot
was re-fetched (3acf8cf, 2026-08-01, recorded the trade-off as a status update on ADR 0017). ADR
0055 later replaced that trust with verification on every hit.

### Consequences

* Good, because a cached model loads with no network access, and the CLI runs offline.
* Good, because cold runs no longer pay for a Hub revalidation.
* Bad, because a registry pin bumped for an updated upstream artifact does not reach a machine
  that still holds the old cached copy until that snapshot is fetched again.

### Confirmation

`ensure_with_env` in `crates/sceptre/src/models/download.rs` returns the path from
`resolve_cached` before it builds an `hf_hub::HFClient`, and the `resolve_cached_*` unit tests in
the same file cover the cache lookup.
