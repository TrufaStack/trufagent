# Phase 40 — Close writes native v2 memory

## Objective

Remove the temporary v1 proposal adapter from `trufagent close` now that native
v2 memory operations exist.

## Boundary

The Git merge gate and Graphify status check still run before any write. After
those checks, close sends each explicit proposal through `MemoryV2Service`,
records the merged commit as `source_commit`, and rebuilds the combined v1/v2
SQLite index.

No proposal becomes governing during close. Human acceptance remains a
separate create-only review event.

## Evidence

- unmerged commits still create neither memory nor index;
- Graphify failure still occurs before memory writes;
- successful close writes `trufagent.memory.v2` proposals;
- proposal provenance contains the confirmed merged commit;
- the combined index finds the new v2 proposal;
- the compact `trufagent.close.v2` CLI result is unchanged.
