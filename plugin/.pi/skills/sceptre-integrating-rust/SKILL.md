---
description: Embed Sceptre OCR in Rust with Reader, decoded images, model providers and structured error handling.
name: sceptre-integrating-rust
---

<!--
AI-RULEZ :: GENERATED FILE — DO NOT EDIT
Content-Hash: blake3:b2628c6a8f284a0f472918b6b4db6a8618444fec3cdce9e987da33df0ee8b1f5
Source-Hash: blake3:21cc9c656d365863ccc3f7cc10bfd89f532d0588e63366a9e2368c5bbc751034
Schema-Version: v1
-->

# Integrating Rust

Add `sceptre = { version = "0.7", features = ["ort-bundled", "download"] }` to Cargo dependencies.
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
