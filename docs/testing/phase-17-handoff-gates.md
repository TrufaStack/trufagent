# Phase 17 — phase handoff gates

Date: 2026-07-31

## Purpose

Prove the delegation state machine and coordinator gates with a deterministic
adapter before enabling provider calls.

## Observation contract

Each phase produces a compact typed handoff. Successful output names evidence
and artifacts. Error output additionally requires a root-cause hint, safe retry,
and stop condition. Raw adapter exceptions are normalized to their type and do
not leak the provider message.

## Acceptance behavior

The dry-run suite demonstrates:

- exactly one invocation for each active phase;
- no invocation for an explicit `none` phase;
- a warning stops the run and returns control before execution;
- a read-only phase claiming a worktree change fails immediately;
- verification without every required evidence name fails;
- adapter exceptions are not retried;
- success, warning, and error produce deterministic observation fields;
- no adapter has network or subprocess capability.

`trufagent delegation dry-run` accepts a compiled protocol plus scripted phase
handoffs. It returns non-zero for warning and error so automation cannot mistake
“needs coordinator review” for completion.

Automatic Claude/Codex invocation remains disabled.
