# Phase 10 — Claude Code adapter evidence

Date: 2026-07-30

## Contract

- Claude exposes thin task/start/end skills.
- Runtime policy is not duplicated in skill prompts.
- Project id is inferred from `.trufagent/config.yaml`.
- Session close never commits Git.
- Memory proposals remain unreviewed and non-governing.
- Graphify supplies scoped structure while Markdown/YAML remains authoritative
  decision memory.

## RED

`tests/test_claude_adapter.py` initially failed because the manifests still
described the LiteLLM fleet, the three v1 skills did not exist, and session
start required a redundant `--project` flag.

## GREEN

- Added `/trufagent`, `/start-session`, and `/end-session` adapters.
- Migrated plugin `init` and `status` away from the legacy dashboard and fleet.
- Updated plugin metadata to `0.4.0`.
- Added project-id inference for `plan prepare` and session start/end.
- Installed `trufagent 0.4.0.dev0` as an editable personal uv tool.
- Replaced the three personal Claude skills with v1 adapters.

## Verification

- Full test suite: `97 passed`.
- Scoped Ruff: `uv run ruff check src tests` passed.
- `git diff --check` passed.
- Both plugin manifests parse as JSON.
- Real session start recovered the compact Phase 9 handoff.
- Real task preparation recovered accepted governing memory.
- Graphify 0.9.30 built the local graph and returned scoped adapter/session
  nodes under an 800-token query budget.

The retired `ui/server.py` remains outside v1. A repository-wide Ruff run
reports 17 pre-existing legacy dashboard violations; they are intentionally
not mixed into this adapter change.
