# Phase 27 — guided task continuation

Date: 2026-07-31

## Goal

Continue a ready unified-task preview without collapsing local work and
read-only model exploration into one implicit action.

## Safe preview record

Ready tasks create a `trufagent.task-preview-record.v1` under ignored project
state. The create-only record contains:

- opaque preview ID and active session;
- SHA-256 task digest, never raw task text;
- signals, route, autonomy, skills, memory IDs, structural targets, warnings,
  and evidence gates;
- Graphify-first disposition and reasons.

## Continuation modes

`task-continue` always requires a second explicit `--confirm`.

Local mode returns `trufagent.local-handoff.v1`. It grants no new authority and
does not execute code; it gives the host the bounded evidence contract.

Shadow mode requires the task text again, verifies its digest, and returns the
budget and provider authorization requirements. It does not invoke a model.
When exploration tier is already `none`, shadow reports `not-needed`.

Previews from a closed or different session are rejected.

## Dogfood

A real low-risk documentation wording task produced a create-only preview and a
confirmed local handoff with six memory references and no warnings. The handoff
authorized the host to update the task-intake continuation documentation.

The run exposed that declared structural symbols were validated but not added
to the Graphify question. `PlanTaskService` now appends those targets to the
query, reducing false target-incomplete results under truncation.
