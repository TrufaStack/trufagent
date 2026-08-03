---
name: review-and-remember
description: Review a completed code change with task-proportional quality checks, then propose only durable project knowledge for Trufagent memory and Graphify. Use after implementation and validation, before declaring work complete, merging, or closing a session; especially when a change introduces decisions, conventions, architectural boundaries, operational consequences, or reusable lessons.
---

# Review and remember

Confirm that the change improves the project, then preserve only context that
will remain useful beyond the current task.

## Review proportionally

Start from the user request, acceptance criteria, diff, and observed validation.
Inspect the axes that the change can materially affect:

- correctness and error handling;
- simplicity and readability;
- ownership, boundaries, dependencies, and duplication;
- security and treatment of untrusted data;
- performance and resource use;
- tests and operational verification.

For small changes, a focused pass is enough. Expand the review for broad,
high-risk, public-interface, data, security, or architectural changes. Report
actionable findings with evidence and location; do not invent issues merely to
fill every axis.

Resolve required findings and rerun affected checks before completion. Keep
optional improvements separate from the requested work.

## Propose durable memory

After the review is clean, identify facts worth carrying forward:

- decisions and their rationale;
- stable project conventions or commands;
- architectural boundaries and ownership;
- confirmed constraints or operational requirements;
- reusable lessons demonstrated by evidence.

Exclude transient progress, raw logs, speculation, secrets, personal data, and
facts already represented adequately. Phrase each proposal compactly with its
scope and evidence. A proposal remains non-governing until the user accepts it.

## Update cartography at a confirmed boundary

Update Graphify only after the implementation state has been confirmed by the
project's workflow, normally after the relevant commit or merge. Treat the graph
as structural cartography and Markdown memory as durable decision context; do
not make either one impersonate the other.

## Handoff

Report:

- review result and any resolved or remaining findings;
- validation evidence;
- proposed memories, clearly marked as proposals;
- whether Graphify is current for the confirmed code state.

For adaptation provenance only, read
[`references/provenance.md`](references/provenance.md).
