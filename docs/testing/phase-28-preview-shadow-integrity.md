# Phase 28 — Preview-to-shadow integrity

Date: 2026-08-03

## Failure capture

The personal task preview knew the user-declared structural symbols, but persisted
only Graphify-discovered targets. When Graphify intentionally abstained, shadow
authorization therefore emitted an empty `required_symbols` list. The lower-level
shadow command also hardcoded `balanced` even when the preview selected `frontier`.

## Recovery

- Persist `required_symbols` independently from `structural_targets`.
- Keep the new field optional with an empty default so v1 preview records remain
  readable.
- Add `delegation shadow --preview` as the integrity-preserving source of signals,
  symbols, session, task digest, and exploration tier.
- Reject symbol and tier overrides when a preview is supplied.
- Resolve the concrete model from the inherited tier unless an explicit model is
  authorized.
- Return a structured shadow invocation specification from `task-continue` without
  persisting or echoing the task text.

## Evidence

- Full pytest suite passes.
- Ruff passes across `src` and `tests`.
- The wheel builds successfully.
- A real JCT preview preserved `resolveChecklistJobType` while Graphify abstained.
- Its continuation preserved `frontier` and generated a preview-bound invocation.
- A historical preview without `required_symbols` remains readable.
- Provider execution was not authorized or attempted.

## Result

Success. Preview authorization and shadow execution now share one immutable source
for routing inputs. Budget and provider confirmation remain intentionally external
human inputs.
