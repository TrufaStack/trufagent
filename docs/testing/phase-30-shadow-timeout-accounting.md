# Phase 30 — Shadow timeout accounting

Date: 2026-08-03

## Failure capture

- Session: `ses_20260803T002842Z_e1d263`
- Goal: one preview-bound, budgeted, read-only exploration canary.
- Result: the provider subprocess exceeded the 180-second boundary.
- The protected JCT worktree remained unchanged.
- The timeout escaped as `TimeoutExpired`, was classified as
  `acceptance-gate`, and produced no usage record.
- The empty ledger incorrectly presented known cost as zero even though work may
  have occurred before process termination.

## Root cause

`CodexShadowRunner.run()` handled completed process failures and invalid completed
responses, but did not translate `subprocess.TimeoutExpired` into a safe adapter
error carrying usage. `ShadowPhaseAdapter` therefore had neither a specific
failure kind nor a record it could append to the fail-closed usage ledger.

## Contained recovery

- Translate `TimeoutExpired` into `ShadowTimeoutError` without exposing captured
  process output.
- Attach a zero-token, unknown-cost usage record to the timeout error.
- Classify the terminal attempt as `provider-timeout` rather than the generic
  `acceptance-gate`.
- Keep `provider-timeout` non-retryable.
- Reject every later provider authorization in that session because prior cost is
  unknown.

## Evidence

- A runner-level regression proves timeout output is not exposed and unknown-cost
  usage survives.
- An adapter regression proves the usage record is persisted and the failure is
  classified as `provider-timeout`.
- A CLI regression proves a later provider authorization is blocked before a
  second invocation.
- The full pytest suite passes.
- Ruff passes across `src` and `tests`.

## Result

Success for future invocations. The historical canary ledger must be repaired with
one explicit unknown-cost record before its session is closed and archived.
