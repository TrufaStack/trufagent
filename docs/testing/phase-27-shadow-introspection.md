# Phase 27 — Shadow introspection and fail-closed accounting

Date: 2026-08-03

## Failure capture

- Session: `ses_20260731T030941Z_210953`
- Goal: one budgeted, read-only exploration canary against the isolated JCT copy.
- Attempt 1: `transient-process`; the response schema was resolved from the target
  project instead of the Trufagent package.
- Attempt 2: `invalid-response`; the provider process completed, but no valid
  `PhaseHandoff` was accepted.
- Both attempts preserved the worktree fingerprint. Execution and verification
  remained disabled.

## Root causes and risks

1. The shadow schema was not packaged with Trufagent.
2. Response incompatibilities collapsed into one opaque error class.
3. The JSON schema allowed `status=error` without expressing the recovery contract
   enforced by the domain model.
4. A completed provider call with an invalid handoff could lose usage accounting.

## Contained recovery

- Package `trufagent/schemas/handoff-schema.json` and resolve it independently of
  the consumer repository.
- Restrict shadow delegate statuses to `success` and `warning`; operational errors
  remain the host adapter's responsibility.
- Accept both `item.text` and `item.content[].text` agent-message shapes.
- Emit only closed diagnostic codes:
  `jsonl-invalid`, `usage-invalid`, `missing-agent-message`, and
  `handoff-schema-invalid`.
- Persist unknown-cost usage before propagating an invalid-response failure.
- Block later provider authorization whenever prior session cost is unknown.

## Evidence

- Full pytest suite passes.
- Ruff passes across `src` and `tests`.
- Wheel builds and includes the packaged schema.
- The packaged status enum is exactly `success | warning`.
- Simulated success, warning, content-block, malformed JSONL, missing-message, and
  invalid-handoff cases are covered.
- The real failed session now contains an unknown-cost usage record and rejects
  further provider calls.

## Result

Partial. The boundary is safer and observable offline, but no valid live handoff has
yet been observed. Do not authorize another provider canary until it uses a fresh
session and receives separate human approval.
