---
status: accepted
date: 2026-10-27
deciders: Na'aman Hirschfeld
---

# Qualify reviewed changes on main

## Context and Problem Statement

Running the same CI matrices on each evolving pull request and again on main consumes runners
before changes are ready. The maintainer requested local review and re-review of updated pull
requests, followed by one qualification pass on ready main.

## Decision Outcome

Remove pull-request triggers from CI, documentation deployment, plugin checks, governance checks
and benchmark checks. Restrict pushes and all jobs in these workflows to `refs/heads/main`,
including manual benchmark dispatches. Retain path filtering, fail-open change detection, every
quality gate, and the existing weekly benchmark schedule on main. A superseding main push can
cancel an older main qualification through the existing concurrency policy.

Release tag publishing, plugin release artifacts and published native runtime verification retain
their existing triggers and guards. Main CI passing does not replace those release gates. Reviews
must use the current PR head; merging a reviewed change does not assert that its subsequent main
qualification has passed.

This amends ADR 0044's triggering policy without changing its job composition or path-filter
semantics. The hosted benchmark still requires a genuinely measured, comparable baseline before
its existing RSS and throughput gates can pass; changing CI triggers does not resolve that hold.
