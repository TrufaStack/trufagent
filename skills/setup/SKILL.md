---
description: Use this skill to set up the trufagent framework globally on this machine — configures LiteLLM, API keys, agent fleet, global CLAUDE.md, and hooks. Run once per machine. Invoke with /trufagent:setup or when the user says "setup trufagent", "configure trufagent", or "install trufagent fleet".
---

# trufagent:setup

Sets up the trufagent framework on this machine. Safe to re-run to reconfigure.

## What this skill does

1. Asks which configuration mode to use
2. Configures each agent role (recommended model shown, alternatives available)
3. Writes `~/litellm-config.yaml`
4. Writes `~/.claude/CLAUDE.md` with fleet rules
5. Copies agent files to `~/.claude/agents/`
6. Configures PostToolUse and PreCompact hooks in `~/.claude/settings.json`

## Step 1 — Check LiteLLM

```bash
pip show litellm 2>/dev/null | head -1
```

If not installed, inform the user to run `pip install litellm[proxy]` and restart setup.

## Step 2 — Choose configuration mode

Ask the user:

```
How would you like to configure your fleet?

  1. Recommended  — multi-provider, optimized cost/quality balance
       scout    → Gemini Flash          ($0.04/M — exploration)
       runner   → Groq Llama 3.3 70B   ($0.05/M — parallel speed)
       thinker  → DeepSeek V4 Flash    ($0.14/M — deep reasoning)
       builder  → Qwen Coder 2.5 32B   ($0.50/M — implementation)
       reviewer → Claude Sonnet        ($3.00/M — code review)
       writer   → Mistral Free         ($0.00/M — commit messages)
       critic   → Claude Sonnet        ($3.00/M — arch review)

  2. Full-stack Claude  — single Anthropic API key, simplest setup
       scout / runner / writer → claude-haiku-4-5
       thinker / builder       → claude-sonnet-4-6
       reviewer / critic       → claude-sonnet-4-6

  3. Custom  — configure each agent individually

Choose [1/2/3]:
```

### Mode 1 — Recommended

For each agent below, ask for the API key of its provider.
Show "Use the recommended model? [Y/n]" — if n, show alternatives.

| Agent | Role | Default model | Provider | Required |
|-------|------|--------------|----------|----------|
| scout | File exploration, grep, parsing | gemini/gemini-2.0-flash | Google AI Studio | Yes |
| runner | Fast parallel tasks | groq/llama-3.3-70b-versatile | Groq | No |
| thinker | Deep reasoning, debugging, algorithm design | deepseek/deepseek-v4-flash | DeepSeek | Yes |
| builder | Full-stack implementation | openrouter/qwen/qwen-2.5-coder-32b-instruct | OpenRouter | Yes |
| reviewer | First-pass code review | anthropic/claude-sonnet-4-6 | Anthropic | Yes |
| writer | Commit messages, changelogs | openrouter/mistralai/mistral-7b-instruct:free | OpenRouter | No |
| critic | Architectural review | anthropic/claude-sonnet-4-6 | Anthropic | No |

**Alternatives per role:**

scout: `anthropic/claude-haiku-4-5`, `openai/gpt-4o-mini`, custom
runner: `anthropic/claude-haiku-4-5`, `openai/gpt-4o-mini`, custom
thinker: `deepseek/deepseek-v4-pro` (more powerful, 12x cost), `anthropic/claude-sonnet-4-6`, `openai/gpt-4o`, custom. Note: `deepseek/deepseek-chat` is deprecated July 24, 2026 — do not use.
builder: `deepseek/deepseek-chat`, `openai/gpt-4o`, `mistral/codestral-latest`, custom
reviewer: `anthropic/claude-opus-4-8` (higher quality, 5x cost), `openai/gpt-4o`, custom
critic: `anthropic/claude-opus-4-8` (highest quality, 5x cost), `openai/gpt-4o`, custom
writer: `anthropic/claude-haiku-4-5`, `openai/gpt-4o-mini`, custom

### Mode 2 — Full-stack Claude

Only ask for `ANTHROPIC_API_KEY`. Map all agents:
- scout, runner, writer → `anthropic/claude-haiku-4-5`
- thinker, builder → `anthropic/claude-sonnet-4-6`
- reviewer, critic → `anthropic/claude-sonnet-4-6`

### Mode 3 — Custom

Walk through each agent one by one. Show role description, ask for model string and API key.

## Step 3 — Write ~/litellm-config.yaml

Generate from the choices made. One `model_name` entry per configured agent. Always include `claude-sonnet-4-6` as the orchestrator entry.

```yaml
model_list:
  - model_name: claude-sonnet-4-6
    litellm_params:
      model: anthropic/claude-sonnet-4-6
      api_key: os.environ/ANTHROPIC_API_KEY
  [... one entry per configured agent ...]

litellm_settings:
  drop_params: true
  request_timeout: 60

general_settings:
  master_key: sk-litellm-local
  port: 4000
```

## Step 4 — Write ~/.claude/CLAUDE.md

Read `templates/global-claude.md` and write to `~/.claude/CLAUDE.md`.
If a CLAUDE.md already exists with other content, append the trufagent section below it.

## Step 5 — Copy agent files to ~/.claude/agents/

Copy all `.md` files from the plugin's `agents/` directory to `~/.claude/agents/`.
Skip optional agents that were not configured.

## Step 6 — Configure hooks in ~/.claude/settings.json

Read current `~/.claude/settings.json`, add or merge:

```json
"hooks": {
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": "echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; d=json.load(sys.stdin); exit(0 if 'git commit' in d.get('command','') else 1)\" 2>/dev/null && PENDING=\"$PWD/docs/context/pending-updates.md\" && [ -f \"$PENDING\" ] && printf '## [%s] commit: %s\\nMessage: %s\\nFiles: %s\\n---\\n' \"$(date '+%Y-%m-%d %H:%M')\" \"$(git log -1 --format='%h' 2>/dev/null)\" \"$(git log -1 --format='%s' 2>/dev/null)\" \"$(git diff-tree --no-commit-id -r --name-only HEAD 2>/dev/null | head -10 | tr '\\n' ',')\" >> \"$PENDING\" || true"}]
    },
    {
      "matcher": "Edit|Write",
      "hooks": [{"type": "command", "command": "FILE=$(echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))\" 2>/dev/null); if [[ \"$FILE\" == *.ts || \"$FILE\" == *.tsx ]]; then PROJ=\"$PWD\"; while [ \"$PROJ\" != \"/\" ] && [ ! -f \"$PROJ/package.json\" ]; do PROJ=$(dirname \"$PROJ\"); done; [ -f \"$PROJ/package.json\" ] && cd \"$PROJ\" && timeout 30 npx tsc --noEmit 2>&1 | grep 'error TS' | head -5; fi || true"}]
    }
  ],
  "PreCompact": [
    {
      "hooks": [{"type": "command", "command": "PENDING=\"$PWD/docs/context/pending-updates.md\"; [ -f \"$PENDING\" ] && printf '## [COMPACTION %s] — context saved before compaction\\n---\\n' \"$(date '+%Y-%m-%d %H:%M')\" >> \"$PENDING\" || true"}]
    }
  ]
}
```

## Step 7 — Final output

```
trufagent setup complete.

Fleet configured ([mode name]):
  scout    → [model]
  runner   → [model]
  thinker  → [model]
  builder  → [model]
  reviewer → [model]
  writer   → [model]
  critic   → [model]

To start using trufagent:

  Terminal 1 — start LiteLLM proxy:
    export ANTHROPIC_API_KEY="sk-ant-..."
    [other keys as configured]
    litellm --config ~/litellm-config.yaml

  Terminal 2 — start Claude Code:
    export ANTHROPIC_BASE_URL="http://localhost:4000"
    export ANTHROPIC_AUTH_TOKEN="sk-litellm-local"
    claude

Next: cd into your project and run /trufagent:init
```
