---
description: List, download and prepare Sceptre multilingual OCR models and inspect backend configuration.
name: sceptre-managing-models
---

<!--
AI-RULEZ :: GENERATED FILE — DO NOT EDIT
Content-Hash: blake3:8c96dd895d636cc85419c33a4767457ad757165f29e9554be0481b89d1220af0
Source-Hash: blake3:2a7689a1ee03315e21c810ba70d3440b78a81a4d0a10b17f3434febf1cb8f7ca
Schema-Version: v1
-->

# Managing Models

Run `sceptre models list --all` to discover models and their cache status.
Download only the required languages with `sceptre models download --lang english --lang korean`;
use `--all` only when all language models are needed. Do not combine `--all` and `--lang`.
Models use the Hugging Face hub cache configured by `HF_HUB_CACHE` or `HF_HOME`.

Inspect the chosen runtime with `sceptre env --format json`. The CLI defaults to ONNX Runtime
and downloading. A pure Rust installation is `cargo install sceptre-cli --no-default-features
--features tract,download`; select `--backend tract` when running it.
MCP support requires the additional `mcp` feature. Do not assume an installed CLI includes MCP.
For offline library use, provide verified model assets or explicit detector and recognizer paths;
do not disable checksum validation to work around a failed model download.
