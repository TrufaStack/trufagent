# Phase 37 — V2 post-merge close

## Objective

Add the compact `trufagent close` vertical slice without breaking the v1 memory
reader or the historical `session end` lifecycle.

## Contract

The request names the merged commit and its base ref, then supplies only the
compact outcome: summary, relevant verifications, decisions, and optional memory
proposals. Close fails before writes unless Git confirms that the commit is an
ancestor of the base ref.

After confirmation, close:

- persists proposals as unreviewed, non-governing v1 Markdown memories;
- records the merged commit as proposal provenance;
- rebuilds the disposable SQLite index from canonical Markdown;
- reports whether Graphify requires an update;
- emits the compact `trufagent.close.v2` result.

This is a reversible compatibility boundary. Existing v1 documents remain
readable and no memory becomes governing without explicit human acceptance.

## Acceptance

- an unmerged commit creates neither memory nor index;
- a merged commit creates compatible reviewable proposals;
- the derived index is immediately searchable and can still be rebuilt;
- Graphify freshness is reported rather than silently mutated;
- the real CLI emits only the compact v2 result.
