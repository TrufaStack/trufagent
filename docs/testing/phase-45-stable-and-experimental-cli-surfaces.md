# Phase 45 — Stable and experimental CLI surfaces

The installed CLI now exposes two explicit entrypoints:

- `trufagent` contains the v2 cycle, transitional plan/session aliases, and
  compact skill list/search operations;
- `trufagent-experimental` preserves historical task previews, delegation,
  shadow, promotion, pilots, and advanced global skill management.

Promotion services, pilot storage, promotion workspaces and reviews, and the
Codex managed-skill surface live under `trufagent.experimental`. Stable CLI
imports and `prepare` do not load them.

The stable help output omits experimental commands rather than merely rejecting
them after parsing. The experimental entrypoint keeps their existing arguments
and response schemas while the transition remains active.

Evidence includes surface contract tests, stable import-boundary subprocesses,
separate essential and experimental gates, full pytest, Ruff, wheel build, and
installed entrypoint help checks.
