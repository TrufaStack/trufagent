# Phase 42 — Independent v2 prepare

## Objective

Remove `PlanTaskService`, coordinator gates, exploration gates, and the legacy
delegation domain from the stable `trufagent prepare` execution path without
changing its compact JSON contract.

## Composition

`PrepareV2Service` now composes only:

- neutral task-signal extraction;
- compact v2 classification, model tier, and phase effort;
- bounded memory and Graphify context through `ContextBuilder`;
- reviewed skill selection through the active catalog;
- the existing `trufagent.prepare.v2` result models.

The v1 extractor still adds its legacy strategy through a lazy import. The
historical `plan` and `task` commands retain `_prepare_from_files` and import
their v1 planner types only after those commands are selected.

## Evidence

- a clean subprocess executes `trufagent prepare` successfully and proves that
  `trufagent.domain.delegation` is absent from `sys.modules` afterward;
- the six-scenario CLI routing matrix remains unchanged;
- question-only intake, memory references, Graphify references, skill phases,
  overrides, model tiers, and effort tests remain green;
- historical task extraction and the full project suite remain green.
