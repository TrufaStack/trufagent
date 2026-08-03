# Phase 24 — durable shadow attempts

Date: 2026-07-31

## Goal

Replace manually asserted retry facts with append-only evidence produced at the
provider boundary.

## Event model

Every shadow call writes a `trufagent.attempt.v1` `started` event before the
runner is invoked. It then appends exactly one terminal event:

- `succeeded`, with the protected worktree fact; or
- `failed`, with a safe failure category and the protected worktree fact.

Events contain a SHA-256 task digest but no task text, prompts, responses,
stdout, stderr, environment values, or secrets. The JSONL repository rejects
duplicate event IDs, duplicate starts, and terminal events without a matching
start.

## Retry derivation

For attempt two, the CLI reads events matching the current session and task
digest. It requires exactly one prior start and one prior failure. The
deterministic retry gate consumes the recorded failure category and worktree
fact; only human confirmation remains a command-line action.

`trufagent delegation attempts . <session-id>` exposes the safe history for
inspection.

## Integration evidence

A fake runner exercises the complete lifecycle:

1. attempt one raises a transient process error;
2. the ledger contains `started` and `failed`;
3. attempt two is separately confirmed;
4. the retry gate reads durable facts;
5. the fake runner succeeds;
6. the ledger contains the second `started` and `succeeded`.

No real provider call is needed for this verification.
