# Phase 44 — Experimental runtime boundary

Delegation protocols, coordinator and exploration gates, supervised retry,
attempt and usage ledgers, shadow adapters, and provider runners now live under
`trufagent.experimental`. Historical CLI commands keep their existing schemas
and behavior through lazy imports; stable `prepare` does not load the package.

The regression suite is split physically:

- essential v2 gate: `uv run pytest tests --ignore=tests/experimental`;
- experimental compatibility gate: `uv run pytest tests/experimental`.

The full suite remains available with `uv run pytest`. Canary and benchmark
scripts import the experimental namespace explicitly. The built wheel is also
checked so namespace moves cannot leave operational commands unpackaged.
