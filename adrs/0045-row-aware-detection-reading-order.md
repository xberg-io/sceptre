---
status: accepted
date: 2026-08-21
deciders: Na'aman Hirschfeld
---

# Row-aware reading order across detection buckets

## Context and Problem Statement

CRAFT grouping returns axis-aligned line boxes and free/rotated quads in separate lists. Concatenating
the lists can strand a borderline rotated word at the end of the page, so sceptre began sorting the
combined regions by vertical center and then left edge. A global center sort fixed the stranded-word
case but broke mixed-height rows: a large central label can have a lower center than the smaller
glyphs beside it, causing a visually horizontal line to be emitted in vertical-center order.

The Chinese parity fixture exposed the regression consistently on Linux, macOS, and Windows. Its
top row was emitted as `东`, `西`, `愚园路` rather than the left-to-right order `西`, `愚园路`, `东`.

## Decision Drivers

- Interleave free quads with horizontal regions by page position.
- Preserve left-to-right order for mixed-height regions on the same visual row.
- Prevent a tall region that overlaps two rows from merging those rows.
- Keep ordering deterministic and backend-independent.

## Considered Options

- **Sort every region by vertical center, then left edge.** Rejected because mixed font sizes and
  tall labels reorder a single visual row.
- **Cluster rows by any vertical overlap.** Rejected because a tall region may overlap two adjacent
  rows and collapse them into one.
- **Cluster nearby centers using the shorter region height, then sort each row by left edge.**
  Chosen because the shorter height bounds row membership without allowing a tall box to bridge
  neighboring rows.

## Decision Outcome

Sort regions by vertical center, scan them into rows, and place a region in the current row only
when its center is within half the shorter of its height and the row's minimum height from the
row's mean center. Sort each completed row by left edge.

### Consequences

- Free and horizontal regions are interleaved in top-to-bottom page order.
- Mixed-height labels on one row retain left-to-right reading order.
- The minimum-height bound prevents a tall label from absorbing an adjacent row.
- The eight-model tier-2 parity corpus retains its exact sceptre snapshots and all reference line
  metrics after the change.
