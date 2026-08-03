# Phase 20 — host coordinator and Graphify benchmark

Date: 2026-07-31

## Host-owned coordination

In embedded skill mode, Claude or Codex is already the active coordinator. The
runtime deterministically classifies the task, selects context and skills, sets
autonomy, and returns the plan. Delegating a second coordinator duplicates
work.

`CoordinatorGateResult` now records a successful `host-owned` handoff and
changes the effective task plan to `coordinator=none`. The raw routing function
keeps its economy coordinator for a future external-orchestrator mode.

## Multi-surface Graphify-first benchmark

Three explicit structural lookups were run against a fresh content-fingerprinted
graph:

| Case | Targets | Time | Models |
| --- | --- | ---: | ---: |
| GF01 | model overrides → delegation compilation | 0.316 s | 0 |
| GF02 | worktree fingerprint → shadow boundary | 0.276 s | 0 |
| GF03 | memory review → SQLite index | 0.278 s | 0 |

All three were target-complete and model-free. Mean latency was 0.290 seconds,
with zero model tokens and no usage ledger events.

The suite lives at `evals/graphify-first.yaml`; the benchmark runner never has a
shadow fallback.
