---
status: accepted
date: 2026-10-14
---

# Link the macOS compiler runtime for bundled ONNX Runtime

## Context and Problem Statement

`ort-sys` 2.0.0-rc.14 removed the Apple compiler-runtime linkage present in rc.13.
Its bundled macOS ONNX Runtime archive still references
`__isPlatformVersionAtLeast` from CoreML availability checks. Rust links with
`-nodefaultlibs`, so Clang's `libclang_rt.osx.a` is not added automatically and a
release CLI fails with an undefined symbol. The compiler-runtime archive exports
that symbol; the failure does not establish a new minimum macOS version.

A release-task linker flag would repair the distributed executable while leaving
Rust library consumers with the same failure.

## Considered Options

- Revert to rc.13, postponing the requested ONNX Runtime upgrade.
- Add a CLI-only linker flag or raise the deployment target.
- Restore compiler-runtime linkage at the core crate's build boundary.

## Decision Outcome

For a macOS target with `ort-bundled` and without `ort-dynamic`, the library build
script asks `CC` (or `clang`) for `libclang_rt.osx.a`, validates the returned archive,
and emits its native search directory and static link directive. Failures identify
the compiler operation and retain its diagnostic output. Ship the build script in
the published library package so downstream applications receive the same fix.

Other target operating systems, dynamic ONNX Runtime, and pure-Rust backends do
not discover or link this compiler runtime. Keep the existing deployment target.
Remove the compatibility workaround when a future `ort-sys` release restores the
required Apple runtime linkage.

## Validation

Compile and execute the actual build script with controlled feature and target
environments. Assert the compiler-runtime link directives for bundled macOS and
the absence of link directives or compiler invocations for the other paths.
Verify missing-compiler errors and the published package's build-script inclusion.
Finally build and exercise the actual packaged release executable.
