# Claude Code adapter

## Purpose

The Claude Code adapter preserves the familiar task and session entry points
without recreating orchestration policy in prompts. Claude gathers input and
presents results; the Trufagent runtime owns classification, effort sizing,
memory retrieval, Graphify scope, skill selection, and session persistence.

## Entry points

| Skill | Runtime operation | Boundary |
| --- | --- | --- |
| `/trufagent` | `plan prepare` | Does not execute when intake is incomplete |
| `/start-session` | `session start` | Reads only the compact prior handoff |
| `/end-session` | `session end` | Never commits; proposals stay non-governing |
| `/trufagent:init` | `init` | Creates only v1 configuration and memory vault |
| `/trufagent:status` | read-only status commands | Does not start infrastructure |

Claude plugin installations namespace plugin skills. A repository installation
therefore exposes names such as `/trufagent:start-session`; copying the three
adapter skills into the personal Claude skills directory preserves the shorter
legacy names.

## Removed legacy behavior

- No mandatory agent fleet or fixed model personas.
- No LiteLLM dependency or API-key routing.
- No `docs/context` shadow memory.
- No automatic Git commits at session close.
- No dashboard process started by task or status commands.

The legacy implementation remains available in Git history. It is not a source
of runtime policy for v1.
