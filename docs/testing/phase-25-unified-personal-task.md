# Phase 25 — unified personal task

Date: 2026-07-31

## Goal

Turn the existing intake, planning, memory, Graphify, skill, and session
components into one practical personal command.

## Command

`trufagent task "<request>"`:

1. opens or reuses the project session;
2. deterministically extracts correctable signals;
3. stops with visible questions when input is insufficient;
4. retrieves governed memory and scoped Graphify context;
5. selects reviewed skills;
6. applies host and Graphify-first routing gates;
7. returns a compact preview and next action.

The default path performs no provider invocation and no worktree mutation.
Optional flags correct important inferences without requiring a TaskSignals
document.

## Privacy boundary

Natural-language task text can contain sensitive operational detail. The
session objective therefore stores only `Personal task <digest>`, never the raw
request. The immediate CLI response may echo the request to its caller, but
session journals do not acquire it implicitly.

## Dogfood

Request:

> Change the help text of the shadow attempts command.

Explicit corrections declared the solution known, localized, and structurally
targeted at `JsonlAttemptRepository`.

Observed preview:

- status `ready`;
- execution-driven, low exploration/execution/verification effort;
- autonomy `proceed`;
- coordinator and exploration tier `none`;
- execution and verification tier `economy`;
- accepted Graphify, coordination, retry, and review-event memories retrieved;
- `JsonlAttemptRepository` present in structural targets;
- no warnings and zero model calls.
