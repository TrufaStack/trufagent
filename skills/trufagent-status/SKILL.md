---
name: trufagent-status
description: Show current trufagent fleet status — which agents are configured, what models they use, and whether LiteLLM is running. Use to quickly audit the current setup.
triggers:
  - /trufagent status
  - trufagent fleet status
  - show trufagent agents
---

# trufagent-status

Shows the current state of the trufagent fleet and infrastructure.

## Execution

### Step 1 — Read current config

```bash
cat ~/litellm-config.yaml 2>/dev/null
```

### Step 2 — Check LiteLLM status

```bash
curl -s http://localhost:4000/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('✓ LiteLLM running')" 2>/dev/null || echo "✗ LiteLLM not running"
```

### Step 3 — Check agent files

```bash
ls ~/.claude/agents/ 2>/dev/null
```

### Step 4 — Display summary

Format output as:

```
trufagent v0.1.0 — Fleet Status
─────────────────────────────────────────────────────
Infrastructure
  LiteLLM:  [✓ running on :4000 | ✗ not running]
  Config:   ~/litellm-config.yaml [found | not found]

Fleet
  scout    [gemini/gemini-2.0-flash]         Google AI Studio  ✓
  runner   [groq/llama-3.3-70b-versatile]    Groq              ✓
  thinker  [deepseek/deepseek-chat]           DeepSeek          ✓
  builder  [openrouter/qwen/...]              OpenRouter        ✓
  writer   [openrouter/mistralai/...]         OpenRouter        ✓
  critic   [anthropic/claude-opus-4-8]        Anthropic         ✓  [optional]

Context System
  Global CLAUDE.md:  [✓ found | ✗ missing — run /trufagent setup]
  Project CLAUDE.md: [✓ found | ✗ missing — run /trufagent init]
  state.md:          [✓ found | ✗ missing — run /trufagent init]
  pending-updates:   [empty | X commits pending review]

Commands
  /trufagent setup          — reconfigure global fleet
  /trufagent init           — initialize current project
  /trufagent config [agent] — swap model for one agent
```

If LiteLLM is not running, show:
```
⚠ Para arrancar LiteLLM:
  litellm --config ~/litellm-config.yaml
```
