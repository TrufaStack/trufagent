# Phase 23 — supervised shadow CLI

Date: 2026-07-31

## Goal

Promote the read-only canary into a discoverable CLI workflow without granting
automatic provider, execution, verification, or retry authority.

## Interaction contract

`trufagent delegation shadow` has three fail-closed layers:

1. semantic applicability and Graphify-first structural sufficiency;
2. prospective session-budget authorization;
3. explicit human confirmation.

Running the command without `--confirm-provider` prepares the route and reports
zero model invocations. The provider is invoked only after confirmation and
only for the exploration step. Coordinator, execution, and verification use
tier `none`.

## Retry contract

Attempt two is a separate command after observing attempt one. It requires:

- a classified `transient-process` failure;
- exactly one prior attempt;
- confirmation that protected worktree content stayed unchanged;
- an authorized prospective budget;
- `--confirm-retry`.

The deterministic retry gate rejects every other failure class. There is no
automatic loop and no third attempt.

## Cost uncertainty

The current Codex adapter records tokens but may record monetary cost as
unknown. A later call cannot prove compliance with a monetary session ceiling
when prior cost is unknown, so authorization fails closed instead of treating
unknown as zero.

## Verification

CLI tests cover preparation with zero queries/invocations, absent retry
confirmation, and rejection of non-transient retries. Provider execution is
not used as a test fixture; adapter and worktree-boundary behavior remain
covered by the existing fake-runner tests.
