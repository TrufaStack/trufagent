# Phase 29 — Local shadow CLI canary

Date: 2026-08-03

## Goal

Exercise the complete personal preview-to-shadow CLI path without network access or
a provider process.

## Fixture

`scripts/run_local_shadow_canary.py` creates a disposable project and replaces the
Codex boundary with one deterministic read-only runner. The fixture records USD
0.02 of synthetic known cost under a USD 0.10 session limit.

## Deterministic judges

1. Preview integrity: declared symbols and frontier tier survive continuation.
2. Route integrity: the runner receives `frontier` and `gpt-5.6-sol`.
3. Handoff integrity: coordinator, execution, and verification remain skipped;
   only exploration succeeds.
4. Accounting integrity: exactly one started/succeeded attempt pair and one usage
   record are persisted.
5. Budget fail-closed: a second USD 0.09 estimate is rejected before the runner is
   called again.

## Result

Three independent runs passed all five judges (3/3, 100% consistency). Every report
recorded `provider_invocations=0` and `simulated_runner_calls=1`. The executable is
also covered by pytest as a subprocess, so its real CLI entry path is exercised.
