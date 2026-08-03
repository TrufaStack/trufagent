# Phase 22 — Graphify abstention and explicit shadow

Date: 2026-07-31

## Goal

Avoid both structural queries and model calls when task semantics already show
that Graphify cannot settle the exploration question.

## Pre-query gate

`evaluate_graphify_applicability()` evaluates typed task signals and declared
targets before the Graphify adapter is called. It abstains for:

- architecture, research, or visual judgment;
- open decisions;
- bugs whose cause is not confirmed;
- external evidence or hypotheses that may negate the work;
- unapproved features or implementation plans;
- small changes without a known solution;
- requests without explicit structural symbols.

The post-query `evaluate_graphify_first()` gate remains responsible for graph
freshness and target completion. This keeps semantic eligibility separate from
structural sufficiency.

## Benchmark

`evals/graphify-first.yaml` now contains three positive and four negative
cases. The live run produced:

| Cases | Expected route | Graph queries | Model invocations |
| ---: | --- | ---: | ---: |
| 3 | model-free | 3 | 0 |
| 4 | shadow-required | 0 | 0 |

All seven cases passed. Positive queries completed in roughly 0.29 seconds
each; semantic abstentions completed below the displayed millisecond
precision.

## Explicit shadow boundary

`scripts/run_shadow_canary.py` accepts a typed `--signals` document. It applies
the pre-query gate and reports both `graph_queries` and `model_invocations`.
Without `--allow-shadow`, it always stops after reporting why supervision is
needed.

The opt-in path remains exploration-only and read-only. Execution and
verification have tier `none`; provider output cannot silently authorize code
changes.
