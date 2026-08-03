---
name: implement-with-evidence
description: Implement fixes, features, and refactors in small verified increments with proof proportional to task complexity and risk. Use after Trufagent preparation when code or behavior must change; especially for bug reproduction, behavior changes, multi-file implementation, or work whose completion must be demonstrated with tests, builds, lint, type checks, or focused runtime checks.
---

# Implement with evidence

Turn the prepared task into the smallest complete change whose behavior can be
demonstrated. Let repository conventions and Trufagent's effort recommendation
set the amount of process.

## Choose the evidence

- For a bug, demonstrate the failure before fixing it when a focused reproducer
  is feasible. If the cause is still unknown, use `systematic-debugging` first.
- For new or changed behavior, identify the observable guarantee and the
  cheapest test that would fail without the change.
- For refactoring, preserve behavior with existing or focused characterization
  tests.
- For configuration, documentation, or static data, use the relevant parser,
  schema, build, lint, or diff check instead of manufacturing a behavioral test.
- Add integration, end-to-end, security, or performance checks only when the
  affected boundary or risk justifies them.

Do not impose a universal coverage percentage, test framework, commit cadence,
or browser check. Discover and follow the repository's actual validation path.

## Implement incrementally

1. Inspect the owning code, nearby tests, and project instructions.
2. State the behavior to prove and the focused validation target.
3. Make one coherent increment within the requested scope.
4. Run the focused validation and diagnose failures before continuing.
5. Repeat only while another increment is necessary for the same acceptance
   criteria.
6. Run the proportionate final checks, including the full suite only when the
   repository or risk warrants it.

Keep each increment understandable and independently reviewable. Do not add
unrequested cleanup, speculative abstractions, global hooks, dependencies, or
feature flags merely to satisfy the workflow.

## Report proof

At handoff, distinguish:

- behavior implemented;
- evidence observed, including commands and outcomes;
- checks not run and why;
- remaining uncertainty or follow-up work.

Never describe an unexecuted check as passing. Continue with
`review-and-remember` when the change is ready for final review.

For adaptation provenance only, read
[`references/provenance.md`](references/provenance.md).
