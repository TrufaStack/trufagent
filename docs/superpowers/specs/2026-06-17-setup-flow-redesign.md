# trufagent setup flow redesign
Date: 2026-06-17

## Problem

The current setup flow has 5 issues:

1. **Silent installation** — `pip install -q` hides all output; LiteLLM takes minutes with no feedback.
2. **Dashboard never opens** — both `/trufagent:setup` and `/trufagent:init` end with text instructions instead of launching the dashboard.
3. **Setup duplicates dashboard** — `/trufagent:setup` asks for API keys and models interactively in the terminal, which is exactly what the dashboard UI already does.
4. **OpenRouter key confusion** — `builder` (qwen) and `writer` (mistral:free) both use `OPENROUTER_API_KEY` but the fleet UI presents them as independent configurations, implying two separate keys.
5. **Gemini test fails** — `test_agent` pings agents through the LiteLLM proxy, which doesn't have the key yet when the user is setting it up for the first time. The key is saved to the FastAPI process env but not inherited by the already-running LiteLLM subprocess.
6. **ANTHROPIC_API_KEY redundancy** — `reviewer`, `critic`, and `designer` are configured as LiteLLM model entries requiring `ANTHROPIC_API_KEY`. These agents run as native Claude Code sub-agents and don't need LiteLLM entries or a separate key.

## Design

### `/trufagent:setup` — simplified to install + open

Remove the interactive terminal Q&A (mode selection, API keys, model choices). The dashboard handles all of that.

New steps:
1. Check if `litellm[proxy]` is installed — if not, run `pip install litellm[proxy]` **without** `-q` so output is visible.
2. Check if dashboard deps are installed (`fastapi uvicorn pyyaml httpx python-dotenv`) — if not, install **without** `-q`.
3. Write `~/litellm-config.yaml` from the base template (no API keys populated — user sets them in the dashboard).
4. Copy agent files to `~/.claude/agents/` (same as before).
5. Configure hooks in `~/.claude/settings.json` (same as before).
6. **Launch the dashboard** (run the dashboard skill steps inline).

### `/trufagent:init` — open dashboard after generating context

After Phase C generates `CLAUDE.md` and `docs/context/`, add a final step that launches the dashboard (same inline steps from dashboard skill). This lets users configure their fleet immediately after initializing a project.

### `templates/litellm-config.yaml` — remove Claude-native agents

Remove `reviewer`, `critic`, `designer` entries. These agents are Claude Code sub-agents — they don't route through LiteLLM. The orchestrator entry (`claude-sonnet-4-6`) stays because it routes the main Claude Code session through the proxy.

Remaining entries: `claude-sonnet-4-6` (orchestrator), `scout`, `runner`, `thinker`, `builder`, `writer`.

### `ui/server.py` — direct key testing

Change `test_agent` endpoint to call the provider directly via `litellm.acompletion()` (Python library, not proxy). This means the test works regardless of whether the LiteLLM proxy is running, and tests the key as provided at that moment.

### `ui/app.js` — shared key grouping

When multiple agents share the same `key_name` (e.g., both `builder` and `writer` use `OPENROUTER_API_KEY`), show a shared badge and only prompt for the key value once. Entering the key value in any agent that shares it fills the others automatically.

## Files changed

| File | Change |
|------|--------|
| `skills/setup/SKILL.md` | Remove terminal Q&A, add visible pip output, end by launching dashboard |
| `skills/init/SKILL.md` | Add dashboard launch at end of Phase C |
| `templates/litellm-config.yaml` | Remove reviewer, critic, designer entries |
| `ui/server.py` | Change `test_agent` to use `litellm.acompletion()` directly |
| `ui/app.js` | Add shared key detection and auto-fill between agents with same key_name |

## Not changed

- Dashboard skill (`skills/dashboard/SKILL.md`) — no changes, setup/init call its steps inline
- Agent `.md` files — reviewer/critic/designer stay as Claude Code sub-agents, unchanged
- Hook configuration — same as before
