# Phase 35 — Generic pilot promotion policy

Date: 2026-08-03

## Boundary clarification

The offline JCT copy is an optional reference and evaluation fixture. Trufagent must
not depend on JCT-specific paths, symbols, frameworks, services, or repository layout.
This rule is accepted as project memory `mem_9e73c1b6d4a8205f71ac`.

## Policy

`trufagent promotion init <root>` creates a generic, local YAML policy requiring:

- a sanitized context projection with secret/data exclusions;
- default-deny external services;
- isolated-worktree writes;
- human review and explicit apply confirmation;
- forbidden push, deploy, migration, and production commands;
- one live canary and ten completed pilot tasks.

The initializer is create-only/idempotent and rejects divergent existing policy.

## Honest readiness

`trufagent promotion status <root>` evaluates observed runtime facts separately from
policy declarations. A strict policy therefore cannot create a false ready result by
itself.

The offline JCT fixture currently reports all seven gates as blocked. This is expected:
the policy exists, but context projection, runtime network enforcement, isolated write
application, operation gates, canary evidence, and the ten-task ledger have not all
been implemented and observed yet.

## Result

Success for the generic policy foundation. Promotion remains blocked by design while
the runtime controls are built in subsequent phases.
