# Phase 16 — bounded delegation

Date: 2026-07-31

This phase introduces contracts and observability before execution authority.

## Enforced invariants

- Four unique phases in deterministic order.
- `max_parallel=1`.
- At most one attempt per phase.
- Worktree writes only during execution.
- Explicit no-invocation representation for `none`.
- Verification inherits the plan's evidence requirements.
- Project model overrides are resolved during compilation.
- Usage models are immutable.
- Per-session JSONL records are append-only and reject duplicate invocation IDs.
- Unknown cost remains distinguishable from zero cost.
- Budget authorization rejects a projected overspend.

## Canary boundary

The protocol compiler and usage recorder do not call a model. The live Terra
C05 validation from Phase 15 is recorded as observed usage for this session,
then a representative C05 protocol is compiled. This checks model resolution,
authority boundaries, evidence transfer, and accounting without paying for or
authorizing a second implementation/verification pass.

Automatic model invocation remains disabled.
