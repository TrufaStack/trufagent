# Phase 34 — Preview freshness seal

Date: 2026-08-03

## Risk

The shadow adapter already proved that protected content did not change during an
invocation, but no gate proved that the repository still matched the state used to
create its task preview. A closed session or a source edit between preview and
authorization could therefore reuse stale routing and Graphify context.

## Gate

- New previews persist the existing source-visible SHA-256 worktree fingerprint.
- `.trufagent` state, Graphify output, dependencies, caches, builds, and Git metadata
  remain excluded by the established fingerprint policy.
- Before constructing a provider runner, preview-bound shadow verifies:
  1. the requested session is still the active session;
  2. the preview belongs to that session;
  3. the preview contains a worktree seal;
  4. the current fingerprint exactly matches the sealed fingerprint.
- Historical unsealed previews remain readable but cannot authorize a provider; they
  must be regenerated.
- The preflight exposes `session_active=true` and `preview_fresh=true` as concrete
  authorization facts.

## Evidence

- A post-preview source edit is rejected before provider-runner construction.
- A preview whose session is no longer active is rejected before preflight.
- A fresh preview reaches provider-free preflight with both gate facts true.
- Real JCT preview `tp_9c4a4f756004b8ff485d` is sealed against session
  `ses_20260803T012508Z_4a4030` and the current local worktree.

## Result

Preview routing, memory selection, Graphify context, budget authorization, and the
actual inspected worktree now form one fail-closed chain. This is the final setup
change before the live canary.
