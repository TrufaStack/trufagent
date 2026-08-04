# Phase 46 — Stable command handlers and graph alias

The stable CLI delegates `prepare`, `close`, `memory`, `graph`, `models`, and
`init` to modules under `trufagent.commands`. The root CLI retains parser and
compatibility dispatch responsibilities while historical handlers remain
available to `trufagent-experimental`.

`graph` is the canonical structural-cartography command. `cartography` remains
an argparse alias during the transition and produces identical JSON and exit
codes. Existing automation can migrate without a flag day.

The extraction removes the old duplicate stable handler bodies from `cli.py`.
Tests patch dependencies at the owning command module, making service
composition boundaries explicit.

Evidence includes focused command regressions, canonical/alias equivalence,
stable import-boundary checks, separate essential and experimental gates, full
pytest, Ruff, wheel build, and both installed CLI entrypoints.
