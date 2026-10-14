---
type: Playbook
title: Tuning Ocr
description: Tune Sceptre detection memory, orientation and language options when OCR misses text or consumes too much memory.
x-ai-rulez:
  kind: skill
  id: sceptre-tuning-ocr
  metadata:
    name: sceptre-tuning-ocr
---

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
