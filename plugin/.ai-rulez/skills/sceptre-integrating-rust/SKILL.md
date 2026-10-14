---
type: Playbook
title: Integrating Rust
description: Embed Sceptre OCR in Rust with Reader, decoded images, model providers and structured error handling.
x-ai-rulez:
  kind: skill
  id: sceptre-integrating-rust
  metadata:
    name: sceptre-integrating-rust
---

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
