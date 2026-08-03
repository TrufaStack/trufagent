# Phase 33 — Shadow preflight and budget reservations

Date: 2026-08-03

## Goal

Close the personal-pilot setup with a human-readable authorization surface and
conservative multi-invocation budget accounting.

## Preflight contract

Before provider confirmation, `delegation shadow` returns a typed
`trufagent.shadow-preflight.v1` observation containing:

- status, summary, next actions, and preview artifact;
- concrete model and tier;
- session budget and authorized estimate;
- target count and target limit;
- inspected-file limit and process timeout;
- prompt character count, without task text;
- selected memory IDs;
- Graphify state, commit, and version;
- explicit read-only fact.

The preflight performs zero provider invocations and does not expose prompts,
responses, or secrets.

## Cost reservation contract

Every real runner usage record keeps two independent values:

- `authorized_estimate_usd`: the amount reserved before invocation;
- `cost_usd`: actual provider-reported cost, when available.

Ledger summaries distinguish `actual`, `estimated`, `unknown`, and `empty` states.
Budget authorization uses actual cost when present and otherwise consumes the full
authorized estimate. A missing actual cost therefore never appears as actual zero.

Legacy or exceptional records with neither actual cost nor an authorized estimate
remain unbounded unknowns and block all later provider authorization. Estimated
records may permit another invocation only when all reservations remain inside the
session ceiling.

## Real offline evidence

Preview `tp_be15567f116cfc9c21b7` produced a provider-free preflight with:

- `gpt-5.6-sol`, frontier;
- USD 0.50 ceiling and USD 0.10 reservation;
- 24 bounded structural targets and a 12-file inspection limit;
- 180-second timeout and a 1,657-character prompt;
- accepted local-only memory;
- fresh Graphify 0.9.30 snapshot at the recorded commit;
- zero graph queries during continuation and zero model invocations.

## Result

These are the final speculative harness improvements before the personal pilot.
Further changes require evidence from real pilot tasks.
