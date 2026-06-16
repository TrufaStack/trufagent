# trufagent

Multi-agent development framework for Claude Code. Manages a fleet of specialized sub-agents routed via LiteLLM, with persistent project context and a structured workflow.

**Author:** [TrufaStack](https://github.com/TrufaStack)

---

## What it does

- **Fleet of 6 specialized agents** — each role is fixed, models are swappable per user
- **LiteLLM routing** — all models go through a local proxy, so you can use any provider
- **Persistent context** — every project gets `CLAUDE.md` + `docs/context/` so Claude never loses project state between sessions
- **Structured workflow** — brainstorm → implement → verify → review → commit, scaled to change complexity
- **Git control** — Claude commits, you push. No surprises.

---

## Fleet

| Agent | Default model | Role |
|-------|--------------|------|
| `scout` | Gemini 2.0 Flash | File exploration, grep, parsing |
| `runner` | Groq Llama 3.3 70B | Fast parallel tasks |
| `thinker` | DeepSeek V3 | Deep reasoning + first review pass |
| `builder` | Qwen Coder 2.5 32B | Full-stack implementation |
| `writer` | Mistral 7B Free | Commit messages, changelogs |
| `critic` | Claude Opus 4.8 | Architecture & security review [optional] |

All models are **reconfigurable** — roles stay fixed, models are swapped in `~/litellm-config.yaml`.

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
/trufagent setup
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `/trufagent setup` | One-time global setup — LiteLLM config, fleet, hooks |
| `/trufagent init` | Per-project init — auto-detects stack, generates CLAUDE.md + context files |
| `/trufagent config [agent]` | Swap the model behind an agent role |
| `/trufagent status` | Show fleet status and LiteLLM health |

---

## How context works

```
~/.claude/CLAUDE.md          → global fleet rules (always loaded)
project/CLAUDE.md            → stack, conventions, restrictions
project/docs/context/
  ├── state.md               → what's done / what's pending
  ├── pending-updates.md     → auto-updated after each git commit
  └── decisions/             → one ADR per important decision
```

At the start of each session, Claude reads these files and proposes updates if commits happened since last session. You approve before anything changes.

---

## License

MIT
