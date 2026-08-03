# Phase 12 — Cross-adapter evaluation

Date: 2026-07-30

## Evaluation layers

Layer 1 is deterministic and cheap. Both Claude Code and Codex adapters call
the same `plan prepare` runtime, so the casebook evaluates their shared
classification contract once. Existing adapter contract tests verify that
neither platform reimplements the policy.

Layer 2 will run real agent trials only for a small representative subset. It
will measure whether each harness follows questions, autonomy boundaries, and
effort budgets in practice. It is intentionally not part of every test run.

## Fixture and metrics

`evals/casebook.yaml` encodes C01–C12. Each case checks:

- task mode;
- exploration, execution, and verification budgets;
- autonomy boundary;
- readiness/blocking;
- required skills;
- required evidence.

Run the CI gate with:

```text
trufagent eval casebook evals/casebook.yaml --fail-under 1
```

## RED baseline

Initial score: 9/12 cases (75%).

- C03 did not recognize a pending interaction decision.
- C06 did not recognize Spanish “corregir” as a bug request.
- C09 did not recognize “API es read-only” as an external constraint.

The baseline also motivated explicitly testing that a small change across two
surfaces retains low effort while requiring both surfaces as evidence.

## GREEN

Final score: 12/12 cases. All eight dimension rates are 100%.

Changes were phrasing- and policy-level generalizations, not case-ID branches:

- added bilingual signals for pending interaction decisions and bug correction;
- expanded read-only API phrasing;
- separated multi-surface evidence from automatic effort escalation for
  genuinely small changes.

## Interpretation

This proves deterministic strategy parity, not end-to-end model obedience.
Live trials remain necessary before claiming equivalent behavior between
Claude and Codex, but they can now focus on three high-information cases rather
than repeating all twelve.
