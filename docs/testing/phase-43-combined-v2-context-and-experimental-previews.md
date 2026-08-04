# Phase 43 — Combined v2 context and experimental previews

The stable `prepare` path reads relevant active Markdown memory from both the
legacy v1 vault and the native v2 vault before applying one context budget.
Compact memory references expose their schema and confirmed source commit when
available, while bodies and local source paths remain outside the host-facing
contract.

Native v2 retrieval includes proposed and accepted documents and excludes
replaced and retired documents. SQLite remains a disposable combined index;
canonical retrieval continues to read Markdown and create-only review events.

Historical task previews and continuation behavior now live under
`trufagent.experimental`. The stable CLI imports them only when a historical
`task`, `task-continue`, or shadow command is selected. Regression tests verify
that importing the CLI and executing stable `prepare` do not load this runtime.

Evidence:

- focused prepare, context, memory-v2, preview, shadow, and import-boundary tests;
- full pytest suite;
- Ruff checks for the changed surface;
- Graphify refresh after the confirmed commit.
