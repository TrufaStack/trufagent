# Phase 26 — unified task dogfood contrasts

Date: 2026-07-31

## Goal

Validate that the unified command spends effort differently for discovery and
approved execution, while keeping its routing decisions visible.

## Ambiguous persistence bug

Request described answers disappearing after navigation, no visible error, and
unknown cause.

Observed preview:

- kind `bug`, cause unknown, persistence and silent failure detected;
- discovery-driven;
- exploration and verification `frontier`;
- execution `balanced`;
- `systematic-debugging` selected;
- reproduction/root-cause and persistence-regression evidence required;
- autonomy `announce`;
- no warnings.

This preserves diagnostic discipline instead of proposing a structural shortcut
or immediate fix.

## Approved implementation

Request referenced an approved plan and declared
`JsonlAttemptRepository` as its structural target.

The first preview exposed `shadow-required` because memory review had changed
protected content after the prior graph build. A direct graph status check
confirmed `dirty_worktree`. After rebuilding Graphify:

- kind `planned-implementation`, approved plan true;
- execution-driven;
- coordinator and exploration `none`;
- execution and verification `frontier`;
- Graphify target complete and `model-free`;
- plan-completion evidence required;
- autonomy `proceed`;
- no warnings.

The CLI preview now includes the exploration disposition and reasons. A user can
therefore distinguish “Graphify saved exploration” from “exploration remained
enabled because structural evidence was stale or incomplete.”

## Privacy review

`mem_47fea53a5ad66698ed87` was accepted with high severity and evidence from the
unified-task tests, Phase 25, and the historical secret-bearing diagnostic
incident.
