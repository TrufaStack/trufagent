# Phase 32 — Safe shadow progress and scope limits

Date: 2026-08-03

## Goal

Finish the personal-pilot setup with two bounded improvements:

1. distinguish provider silence from observable progress without retaining output;
2. stop delegates from expanding a focused investigation into a repository-wide scan.

## Safe progress contract

Terminal attempt events may now contain only:

- elapsed milliseconds;
- number of valid JSONL event envelopes observed;
- the first event type normalized to a closed enum.

Prompts, response bodies, command output, thread identifiers, tool arguments, and
secrets are never persisted. Timeout and invalid-response errors carry this compact
progress object to the create-only attempt ledger. The existing started event remains
the durable invocation-start milestone.

## Inspection contract

- Preview context remains capped at 24 structural targets.
- A delegate may inspect at most 12 files.
- Every inspected path must be returned in `inspected_files`.
- The packaged response schema enforces `maxItems: 12`.
- If a supported conclusion cannot be reached within the limit, the delegate must
  stop early with `status=warning` rather than continue scanning.

## Evidence

- Timeout regression observes two valid event envelopes while discarding a partial
  payload containing a secret-shaped marker.
- Attempt-ledger regression persists only elapsed time, count, and normalized first
  event type.
- Domain and packaged-schema regressions reject more than 12 inspected files.
- Prompt regression includes the early-warning instruction.
- Full pytest, Ruff, offline wheel build, and provider-free local canary pass.

## Result

The setup boundary is complete for the personal pilot. Further harness work should be
driven only by failures observed during real tasks, not by speculative capability
expansion.
