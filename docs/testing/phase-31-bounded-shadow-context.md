# Phase 31 — Bounded shadow context

Date: 2026-08-03

## Failure capture

The first preview-bound JCT canary reached the fixed 180-second process timeout.
It used frontier/high reasoning against a 1.9 GB checkout. The task preview retained
`resolveChecklistJobType`, but its structural targets were empty and the live runner
prompt contained neither the required symbol nor any Graphify result.

## Root-cause diagnosis

The strongest locally supported cause is unbounded exploration:

1. Graphify applicability combined two different decisions: whether structural
   context was useful and whether structural evidence could replace model judgment.
2. An unknown-cause bug therefore skipped Graphify entirely, even though its exact
   symbol resolved locally to the implementation and five persistence endpoints in
   under one second.
3. The shadow runner discarded preview structural context and supplied only the broad
   natural-language task to a high-reasoning delegate.
4. The nested Codex process also inherited user configuration that is unnecessary for
   a constrained read-only delegate.

The captured provider stream was intentionally not retained, so this diagnosis does
not claim whether the delegate was reasoning, scanning, or waiting during the final
seconds.

## Contained recovery

- Collect Graphify context for structurally relevant tasks even when model judgment
  remains mandatory.
- Keep Graphify abstention semantics: an unknown cause still routes to shadow rather
  than treating cartography as the answer.
- If supplemental cartography is unavailable, preserve the model fallback; only
  block when Graphify was required to justify a model-free route.
- Pass required symbols and at most 24 immutable preview targets into the delegate
  prompt.
- Tell the delegate to begin with those targets, avoid repository-wide scans, and not
  load general session history for the bounded subtask.
- Run nested Codex with `--ignore-user-config` while retaining explicit model,
  sandbox, approval, schema, and project settings.

## Evidence

- A real offline JCT preview now contains the resolver, all five persistence endpoint
  route targets, and nearby structural symbols while retaining frontier exploration.
- Prompt regressions prove the required symbol is present and target count is capped
  at 24.
- Routing regressions prove Graphify context supplements rather than replaces model
  judgment.
- The deterministic local shadow canary remains provider-free.

## Result

The known unbounded-exploration path is removed without increasing the timeout. A
future live canary still requires a fresh session, separate budget authorization, and
must be treated as an experiment rather than proof that every provider-side timeout is
resolved.
