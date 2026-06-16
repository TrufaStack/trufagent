---
name: trufagent-setup
description: Run this skill to set up the trufagent framework globally — installs LiteLLM config, configures the agent fleet interactively (API keys per provider), writes global CLAUDE.md, and sets up hooks in settings.json. Run once per machine.
triggers:
  - /trufagent setup
  - setup trufagent
  - configure trufagent fleet
---

# trufagent-setup

Sets up the trufagent framework on this machine. Run once. Safe to re-run to reconfigure.

## What this skill does

1. Checks LiteLLM is installed
2. Configures each agent role interactively (recommended model shown, alternatives available)
3. Writes `~/litellm-config.yaml`
4. Copies `~/.claude/CLAUDE.md` with fleet rules
5. Copies agent files to `~/.claude/agents/`
6. Configures PostToolUse and PreCompact hooks in `~/.claude/settings.json`

## Step-by-step execution

### Step 1 — Check LiteLLM

Run: `pip show litellm 2>/dev/null | head -1`

If not installed: `pip install litellm[proxy]`

### Step 2 — Configure each agent role

For each role below, show the role name, what it does, recommended model and provider, then ask:
- "¿Usás el modelo recomendado? [S/n]"
  - S → ask for API key for that provider → test with a simple ping
  - n → show alternatives list → allow custom LiteLLM model string → ask for API key

**Roles and defaults:**

| Role | Purpose | Default model | Provider | Required |
|------|---------|--------------|----------|----------|
| scout | File exploration, grep, parsing | gemini/gemini-2.0-flash | Google AI Studio | Yes |
| runner | Fast parallel tasks | groq/llama-3.3-70b-versatile | Groq | No |
| thinker | Deep reasoning + first review | deepseek/deepseek-chat | DeepSeek | Yes |
| builder | Full-stack implementation | openrouter/qwen/qwen-2.5-coder-32b-instruct | OpenRouter | Yes |
| writer | Commit messages, changelogs | openrouter/mistralai/mistral-7b-instruct:free | OpenRouter | No |
| critic | Architecture & security review | anthropic/claude-opus-4-8 | Anthropic | No |

**Alternatives per role (show when user says no to recommended):**

scout alternatives:
- `anthropic/claude-haiku-4-5` (Anthropic — already have key)
- `openai/gpt-4o-mini` (OpenAI)
- Custom model string

runner alternatives:
- `anthropic/claude-haiku-4-5` (Anthropic)
- `openai/gpt-4o-mini` (OpenAI)
- Custom model string

thinker alternatives:
- `anthropic/claude-sonnet-4-6` (Anthropic — already have key)
- `openai/gpt-4o` (OpenAI)
- `google/gemini-2.5-pro` (Google)
- Custom model string

builder alternatives:
- `deepseek/deepseek-chat` (DeepSeek)
- `openai/gpt-4o` (OpenAI)
- `mistral/codestral-latest` (Mistral)
- Custom model string

critic alternatives:
- `anthropic/claude-sonnet-4-6` (Anthropic — cheaper, less powerful)
- `openai/gpt-4o` (OpenAI)
- Custom model string

**Anthropic-only mode** (if user declines all non-Anthropic providers):
```
💡 Podés usar solo tu Anthropic API key para todos los roles.
   scout/runner/writer → claude-haiku-4-5
   thinker/builder     → claude-sonnet-4-6
   critic              → claude-opus-4-8
   ¿Querés arrancar con este modo? [S/n]
```

### Step 3 — Write ~/litellm-config.yaml

Generate config from the choices made. Use the template in `templates/litellm-config.yaml` as base, replacing model strings and keeping only configured agents.

### Step 4 — Write ~/.claude/CLAUDE.md

Copy `templates/global-claude.md` to `~/.claude/CLAUDE.md`. If a CLAUDE.md already exists, append the trufagent section below any existing content rather than overwriting.

### Step 5 — Copy agent files to ~/.claude/agents/

Copy all `.md` files from the plugin's `agents/` directory to `~/.claude/agents/`. For any agent not configured (optional + skipped), skip its file.

### Step 6 — Add hooks to ~/.claude/settings.json

Add the following hooks block to `~/.claude/settings.json`. If hooks already exist, merge carefully:

```json
"hooks": {
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": "echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; d=json.load(sys.stdin); exit(0 if 'git commit' in d.get('command','') else 1)\" 2>/dev/null && PENDING=\"$PWD/docs/context/pending-updates.md\" && [ -f \"$PENDING\" ] && printf '## [%s] commit: %s\\nMensaje: %s\\nArchivos: %s\\n---\\n' \"$(date '+%Y-%m-%d %H:%M')\" \"$(git log -1 --format='%h' 2>/dev/null)\" \"$(git log -1 --format='%s' 2>/dev/null)\" \"$(git diff-tree --no-commit-id -r --name-only HEAD 2>/dev/null | head -10 | tr '\\n' ',')\" >> \"$PENDING\" || true"}]
    },
    {
      "matcher": "Edit|Write",
      "hooks": [{"type": "command", "command": "FILE=$(echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))\" 2>/dev/null); if [[ \"$FILE\" == *.ts || \"$FILE\" == *.tsx ]]; then PROJ=\"$PWD\"; while [ \"$PROJ\" != \"/\" ] && [ ! -f \"$PROJ/package.json\" ]; do PROJ=$(dirname \"$PROJ\"); done; [ -f \"$PROJ/package.json\" ] && cd \"$PROJ\" && timeout 30 npx tsc --noEmit 2>&1 | grep 'error TS' | head -5; fi || true"}]
    }
  ],
  "PreCompact": [
    {
      "hooks": [{"type": "command", "command": "PENDING=\"$PWD/docs/context/pending-updates.md\"; [ -f \"$PENDING\" ] && printf '## [COMPACTACIÓN %s] — contexto guardado antes de compactar\\n---\\n' \"$(date '+%Y-%m-%d %H:%M')\" >> \"$PENDING\" || true"}]
    }
  ]
}
```

### Step 7 — Final summary

Show what was configured:
```
✓ LiteLLM config: ~/litellm-config.yaml
✓ Global CLAUDE.md: ~/.claude/CLAUDE.md
✓ Agents: [list configured agents]
✓ Hooks: PostToolUse (git commit, tsc check) + PreCompact

Para arrancar LiteLLM:
  export ANTHROPIC_API_KEY="..."
  [other keys as configured]
  litellm --config ~/litellm-config.yaml

Próximo paso: /trufagent init en tu proyecto
```
