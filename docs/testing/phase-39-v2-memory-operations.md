# Phase 39 — V2 memory operations

## Objective

Make compact v2 memory writable and maintainable through four explicit human
operations while preserving v1 reads and a disposable combined index.

## Storage boundary

Native v2 documents live under `.trufagent/memory/project/v2/`. The historical
v1 repository continues reading its existing non-recursive project and team
roots, so introducing v2 documents cannot break v1 parsing. The v2 surface
combines both sources when listing or rebuilding the SQLite index.

## Operations

- `propose` creates an immutable native v2 Markdown document;
- `accept` appends a review event and requires a named human reviewer;
- `replace` requires both the original and replacement to be accepted;
- `retire` removes proposed or accepted memory from active recall.

Review events are create-only. They never rewrite the original proposal. The
event chain rejects mismatched IDs, invalid transitions, and timestamps older
than the effective state.

The stable `memory` CLI detects v2 documents for `propose`, `accept`, `show`,
`history`, and `list`, and adds the explicit `replace` and `retire` operations.
The v1 `reject` and `supersede` commands remain compatibility aliases.

## Evidence

- native v2 proposals are create-only, non-governing, and indexed;
- acceptance becomes governing only after a human review event;
- replacement requires an accepted replacement;
- retired and replaced memories disappear from indexed recall;
- the CLI completes propose, accept, and retire without using v1 events;
- existing v1 memory and review tests remain green.
