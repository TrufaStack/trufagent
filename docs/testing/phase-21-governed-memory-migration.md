# Phase 21 — governed memory migration

Date: 2026-07-31

## Review enrichment

`MemoryReviewEvent` can now attach optional applicability, evidence, relations,
and validity. The source Markdown remains create-only; effective accepted
memory overlays review metadata while retaining full event history.

The CLI supports:

```bash
trufagent memory propose <project-root> <document> --project <name>
trufagent memory accept <project-root> <id> --project <name> \
  --reviewer <human> --metadata <review.json>
```

Review transitions are validated completely before event creation. A regression
test uses a clock older than the memory and proves no `.events` directory is
created.

## Retry decision

The absolute one-attempt rule was revised after the Phase 18 canary. ADR-0007
supersedes ADR-0006 and permits exactly one supervised retry only for a
transient provider-process failure with:

- one prior attempt;
- unchanged protected-content fingerprint;
- renewed budget authorization;
- explicit human confirmation.

Invalid responses, acceptance-gate failures, worktree changes, and budget
failures remain non-retryable.

## Memory outcomes

Accepted and governing:

- `mem_delegation_retry_v2`;
- `mem_4f60d369a24d5674de76` — Graphify-first;
- `mem_d4f0c3150bf67b52f5c3` — host-owned coordination.

Rejected with audit reason:

- `mem_d1a1d84e901ab04248ae` — absolute one-attempt delegation.

Reviewer: `trufastack`.

## Partial-event incident

The first acceptance attempt for `mem_delegation_retry_v2` used a proposal
timestamp slightly ahead of the system clock. The old implementation wrote the
review event before discovering `updated_at < created_at`.

The invalid event was moved intact and recoverably to
`.trufagent/state/quarantine/`; it was not deleted or included in effective
history. The repository now prevalidates transitions, closing this failure
mode.
