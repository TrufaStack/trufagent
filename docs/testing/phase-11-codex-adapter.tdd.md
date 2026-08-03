# Phase 11 — Codex adapter evidence

Date: 2026-07-30

## Contract

- Expose `$trufagent`, `$start-session`, and `$end-session`.
- Keep frontmatter limited to native Codex `name` and `description`.
- Keep runtime policy authoritative.
- Avoid shell-specific interpolation of task data and close requests.
- Preserve governed-memory and no-commit boundaries.

## RED

The initial `skill-creator` templates failed all three adapter contract tests:
they contained placeholders and no runtime workflow.

## GREEN

- Created three concise native skills under `adapters/codex/skills/`.
- Generated matching `agents/openai.yaml` metadata.
- Installed all three skills into the personal Codex skill directory.
- Reused the globally installed editable `trufagent` executable.

## Verification

- All three source and installed skills pass the official `quick_validate.py`.
- Adapter contract tests pass.
- A real `$start-session`-equivalent invocation recovered the Phase 10 handoff.
- A real localized-change intake selected low exploration, execution, and
  verification effort.
- The same plan retrieved accepted memory and scoped Graphify 0.9.30 context.
