---
description: Embed Sceptre OCR in Rust with Reader, decoded images, model providers and structured error handling.
name: sceptre-integrating-rust
---

<!--
AI-RULEZ :: GENERATED FILE — DO NOT EDIT
Content-Hash: blake3:8a2764e592fca4078d462d08b57a3bed76460dc415af41bc7ff745857663b731
Source-Hash: blake3:9c178e239df0c920c0243b02d5690efd91aa0fd88e3be58623814b0836264ff2
Schema-Version: v1
-->

# Integrating Rust

Add `sceptre = { version = "0.8", features = ["ort-bundled", "download"] }` to Cargo dependencies.
The library default features are empty; select a backend explicitly.

```rust
use sceptre::{ReadOptions, Reader};
use std::path::Path;

let reader = Reader::builder().build()?;
let result = reader.readtext(Path::new("receipt.png"), &ReadOptions::default())?;
```

Reuse the reader across images. Call `warm_up()` or build with `build_warmed()` to move model
initialization out of the first request. Structured lines expose text, confidence and quadrilateral.
For encoded bytes, decode with `Image::from_bytes`, then call `Reader::recognize(&image, &options)`.
`Reader::detect` and `Reader::recognize_line` also accept decoded `Image` values.

Configure the reader through `Reader::builder().config(OcrConfig::default())`;
provide a `ModelProvider` through `.model_provider(...)` for managed or offline assets.
Propagate `OcrError` with the failed operation's context; do not convert errors into empty text.
