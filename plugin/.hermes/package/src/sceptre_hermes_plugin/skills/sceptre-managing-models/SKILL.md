---
description: List, download and prepare Sceptre multilingual OCR models and inspect backend configuration.
name: sceptre-managing-models
---

<!--
AI-RULEZ :: GENERATED FILE — DO NOT EDIT
Content-Hash: blake3:e9904a95a0c02e2df027f29da22800e7b25cd70ed0f529936f9cea53e34509fb
Source-Hash: blake3:5ba6fce721d21bf8c19016b9b5f38557791b36501f70d78b30db765130749cb5
Schema-Version: v1
-->

# Managing Models

Run `sceptre models list --all` to discover models and their cache status.
Download only the required languages with `sceptre models download --lang english --lang korean`;
use `--all` only when all language models are needed. Do not combine `--all` and `--lang`.
Models use the Hugging Face hub cache configured by `HF_HUB_CACHE` or `HF_HOME`.

Inspect the chosen runtime with `sceptre env --format json`. The CLI defaults to ONNX Runtime
and downloading. A pure Rust installation is `cargo install sceptre-cli --locked --no-default-features
--features tract,download`; select `--backend tract` when running it.
MCP support requires the additional `mcp` feature. Do not assume an installed CLI includes MCP.
For offline library use, provide verified model assets or explicit detector and recognizer paths;
do not disable checksum validation to work around a failed model download.
