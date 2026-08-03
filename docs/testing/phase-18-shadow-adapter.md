# Phase 18 — read-only shadow adapter

Date: 2026-07-31

## Boundary

The first provider adapter supports Codex coordinator and exploration phases
only. It is not exposed as a general CLI command. The evaluation script creates
a protocol with coordinator, execution, and verification set to `none`, leaving
one balanced exploration invocation.

Codex runs with sandbox `read-only`, approval policy `never`, an ephemeral
session, strict handoff JSON schema, compact previous handoffs rather than
transcripts, and a 180-second process timeout.

## Worktree protection

The adapter hashes paths and content before and after invocation. Unlike
`git status`, this detects edits to files that were already untracked and to
ignored sensitive files such as `.env`.

Only explicit ephemeral directories are excluded: VCS metadata, virtual
environments, dependency/cache directories, Graphify output, and
`.trufagent/state`. Symlink targets are included in the fingerprint.

Usage is recorded after every structurally valid provider result even if a
later coordinator gate rejects it, because rejected calls still consume tokens.

## First live canary

The first Terra exploration canary stopped safely with
`ShadowProviderError`. It produced no accepted handoff, no usage record, and no
worktree change. The boundary intentionally did not expose provider stdout or
stderr, but its initial error category was too broad to distinguish process
failure from response validation.

No automatic retry was made. The adapter now uses safe subclasses:

- `ShadowProcessError` with `process-exit-N`;
- `ShadowResponseError` with the validation exception type.

These codes preserve diagnosis without crossing provider output through the
adapter boundary.

## Supervised second canary

After the safe taxonomy was installed, one supervised repeat succeeded. Terra
returned a compact exploration handoff describing the path from
`load_model_overrides()` through `compile_delegation_protocol()`, with source
and test artifact paths.

The resulting protocol report had:

- coordinator, execution, and verification explicitly skipped;
- exploration successful;
- no stopped phase;
- an unchanged protected-worktree fingerprint;
- exactly one append-only usage event.

Observed usage was 70,003 input tokens, 46,336 cached input tokens, and 873
output tokens. Monetary cost was unavailable and remains marked unknown.

Because the same code succeeded on the supervised repeat, the first failure is
classified as transient or provider-response-specific but remains
undetermined; it is not erased or relabelled as a pass.

Shadow exploration is now technically validated. It remains evaluation-only,
not automatic delegation authority.
