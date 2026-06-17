# trufagent

Multi-agent development framework for Claude Code. Manages a fleet of 7 specialized sub-agents routed via LiteLLM, with persistent project context and a structured workflow.

**Author:** [TrufaStack](https://github.com/TrufaStack)

---

## What it does

- **Fleet of 7 specialized agents** — roles are fixed, models are swappable per user
- **LiteLLM routing** — all sub-agents route through a local proxy (any provider supported)
- **Three setup modes** — Recommended multi-provider / Full-stack Claude / Custom
- **Persistent context** — every project gets `CLAUDE.md` + `docs/context/` with categorized memory
- **Structured workflow** — brainstorm → design → implement → review → commit, scaled to change complexity
- **Git control** — Claude commits, you push. No surprises.

---

## Fleet

| Agent | Default model | Role |
|-------|--------------|------|
| `scout` | Gemini 2.0 Flash | File exploration, grep, parsing ($0.04/M) |
| `runner` | Groq Llama 3.3 70B | Fast parallel tasks ($0.05/M) |
| `thinker` | DeepSeek V4 Flash | Root-cause debugging, algorithm design, architecture ($0.14/M) |
| `builder` | Qwen Coder 2.5 32B | Full-stack implementation ($0.50/M) |
| `reviewer` | Claude Sonnet | First-pass code review: logic, bugs, types ($3.00/M) |
| `writer` | Mistral 7B Free | Commit messages, changelogs ($0.00/M) |
| `critic` | Claude Sonnet | Architectural review: security, coupling [optional] ($3.00/M) |

All models are **reconfigurable** — roles stay fixed, models are swapped in `~/litellm-config.yaml`.

**Why reviewer and thinker are separate:** DeepSeek excels at reasoning and design; Claude Sonnet detects subtle implementation bugs better. Using the right model for each task improves quality without increasing cost on routine work.

---

## Requirements

- [Claude Code](https://claude.ai/code)
- [LiteLLM](https://github.com/BerriAI/litellm) — `pip install litellm[proxy]`
- API keys for your chosen providers (Anthropic key required for Claude Code)

---

## Installation

```bash
claude plugins install github:TrufaStack/trufagent
```

Then run setup:
```
/trufagent:setup
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `/trufagent:dashboard` | **Open local config UI** — browser-based fleet config, API keys, LiteLLM control |
| `/trufagent:setup` | One-time global setup via CLI — choose fleet mode, configure API keys, install hooks |
| `/trufagent:init` | Per-project init — auto-detects stack, generates CLAUDE.md + context files |
| `/trufagent:config [agent]` | Swap the model behind an agent role (CLI) |
| `/trufagent:status` | Show fleet status and LiteLLM health (CLI) |

## Dashboard UI

Type `/trufagent:dashboard` in Claude Code to open the local configuration UI at `http://localhost:7433`.

```
fleet    → Configure agents: model string (any LiteLLM provider), API key per agent,
           connection test + validation before save. Auto-generates litellm-config.yaml.
status   → Real-time health: LiteLLM proxy status + latency ping for each agent.
litellm  → Start/stop the LiteLLM proxy, view required env vars, copy start command.
projects → List initialized projects, initialize new ones with context/ structure.
```

**Tech:** FastAPI + vanilla HTML/CSS/JS. Binds to 127.0.0.1 only. Requires Python (already needed for LiteLLM).

**Install UI deps:** `pip install fastapi uvicorn pyyaml httpx python-dotenv`

---

## How context works

```
~/.claude/CLAUDE.md              → global fleet rules (always loaded)
project/CLAUDE.md                → stack, conventions, constraints
project/docs/context/
  ├── state.md                   → what's done / in progress / pending
  ├── pending-updates.md         → auto-updated after each git commit (hook)
  └── decisions/
      ├── technical/             → stack, architecture, tool choices
      ├── lessons/               → mistakes made and what we learned
      ├── preferences/           → how the team likes to work
      └── goals/                 → long-term project objectives
```

At the start of each session, Claude reads these files and proposes updates if commits happened since last session. You approve before anything changes.

---

## Workflow

```
Simple change (1 file, no DB):
  builder → reviewer → Claude → Commit

New feature (DB migration, external integration):
  thinker → builder → reviewer → critic → Claude → Commit

Architecture change (irreversible, auth, prod):
  thinker → builder → reviewer → critic → Claude → /code-review ultra → Commit
```

---

## Starting LiteLLM

```bash
# Terminal 1 — start proxy
export ANTHROPIC_API_KEY="sk-ant-..."
export DEEPSEEK_API_KEY="..."      # for thinker
export GEMINI_API_KEY="..."        # for scout
export GROQ_API_KEY="..."          # for runner
export OPENROUTER_API_KEY="..."    # for builder + writer
litellm --config ~/litellm-config.yaml

# Terminal 2 — start Claude Code
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_AUTH_TOKEN="sk-litellm-local"
claude
```

---

## License

MIT
