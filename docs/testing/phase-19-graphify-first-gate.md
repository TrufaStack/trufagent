# Phase 19 — Graphify-first value gate

Date: 2026-07-31

## Goal

Avoid model exploration when scoped structural cartography already provides
the declared evidence.

## Gate

The deterministic gate combines task semantics, graph freshness, explicit
targets, and target coverage. It never infers sufficiency from node count.

The shortcut is prohibited for unknown-cause bugs, architecture, research,
visual design, unapproved features/plans, open decisions, external evidence,
stale or missing graphs, and absent required symbols.

Target-complete truncated results are accepted because omitted unrelated nodes
do not weaken explicit symbol evidence. Missing targets still escalate.

## Dirty-worktree freshness

Graphify manifests now include a protected-content fingerprint. This
distinguishes a fresh snapshot of uncommitted/untracked code from a graph that
became stale after another edit.

## Comparative canary

Question: locate `load_model_overrides()` and
`compile_delegation_protocol()`.

| Route | Elapsed | Model input | Model invocations |
| --- | ---: | ---: | ---: |
| Terra shadow, Phase 18 | about 27 s | 70,003 | 1 |
| Graphify-first | 0.283 s | 0 | 0 |

The model-free route returned only
`src/trufagent/infrastructure/model_profiles.py` and
`src/trufagent/application/delegation.py`. This is roughly a 99% latency
reduction and eliminates all model tokens. The usage ledger remained empty.

An earlier evaluation attempt exposed an unsafe implicit shadow fallback. It
was blocked and recorded no usage. The harness now requires
`--allow-shadow`; default behavior stops with `shadow-required`.
