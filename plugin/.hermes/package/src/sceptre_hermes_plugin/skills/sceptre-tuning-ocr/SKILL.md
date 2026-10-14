---
description: Tune Sceptre detection memory, orientation and language options when OCR misses text or consumes too much memory.
name: sceptre-tuning-ocr
---

<!--
AI-RULEZ :: GENERATED FILE — DO NOT EDIT
Content-Hash: blake3:ad5a2fb97e28a0deefac8858dd0fb2b325625476f642d91546b5f997b79b4c15
Source-Hash: blake3:838e0729665e45091c8b001bac71aa502671c6c390dd8e87276f2d8fd0b917f5
Schema-Version: v1
-->

# Tuning Ocr

Record a baseline image, language configuration and JSON output before changing settings.
Use `--timings` for CLI stage timings and `--threads` for the worker budget.
For large pages, lower `--canvas-size` (default 2560) or cap `--max-megapixels`; this trades
recognition quality against detection memory. Change one setting at a time.

For rotated scans, enable `--detect-orientation`; adjust `--orientation-probe-canvas-size`
and `--orientation-margin` only after inspecting probe results.
`--text-threshold` and `--link-threshold` are probabilities between zero and one.
Lower detection thresholds may admit noise; higher thresholds can discard real text.

Compare absolute correct line/word counts against the source image, confidence and boxes.
Do not judge improvements by a ratio over shortened output. Preserve low-confidence lines for review.
MCP runtime settings belong to `sceptre mcp` startup; they are not per-call tool arguments.
