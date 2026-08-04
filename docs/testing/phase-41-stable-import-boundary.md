# Phase 41 — Stable import boundary

## Objective

Begin Phase 4 by preventing the stable CLI import path from loading delegation,
shadow, retry, attempt, and usage implementations.

## Boundary

The historical `delegation` command remains available as a compatibility alias,
but imports its runtime only after that command is selected. Importing
`trufagent.cli` for `prepare`, `close`, or memory operations no longer loads
those modules.

`domain.delegation` remains a temporary data-contract dependency because the v2
prepare projection still adapts `PlanTaskService`, whose coordinator and
exploration gate results reference that domain model. Removing it belongs to
the next cut; no provider runner, retry policy, attempt store, or usage ledger
is loaded through this exception.

Task previews remain in the main CLI temporarily because `task` and
`task-continue` still own their compatibility contract. They are the next
isolation cut.

## Evidence

A clean Python subprocess imports `trufagent.cli` and asserts that none of the
delegation, shadow, retry, attempt, or usage modules appear in `sys.modules`.
The existing delegation and shadow suites continue to exercise their legacy
commands through the lazy boundary.
