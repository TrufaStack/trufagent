# trufagent — Global Framework

## Agent Fleet

| Agent | Model | When to use |
|-------|-------|-------------|
| `scout` | gemini-flash | Exploration: read files, grep, list directories, parse logs |
| `runner` | groq-llama | Speed: independent parallel tasks, fast conversions |
| `thinker` | deepseek-v4-flash | Deep reasoning: debugging root causes, algorithm design, architecture decisions |
| `builder` | qwen-coder | Implementation: components, APIs, CRUD, full features |
| `reviewer` | claude-sonnet | First-pass code review: logic, bugs, types, conventions |
| `writer` | mistral-free | Non-critical text: commit messages, changelogs |
| `critic` | claude-sonnet | Deep architectural review: security, irreversibility, coupling [optional] |
| `designer` | claude-sonnet | UI/UX design: pages, components, mockups, visual redesigns |

**Orchestrator:** Claude Sonnet — makes delegation decisions, holds full project context, final review pass, writes commits, handles important documentation.

## Delegation

Always announce before delegating:
> `→ delegating to [agent] because [reason]`

## Workflow

**Simple change** (single file, no DB, no new route):
```
Implement (builder) → Review (reviewer → Claude) → Commit
```

**New feature** (DB migration, external integration, multiple modules):
```
Brainstorm → Spec → Design (thinker) → Implement (builder) → Review (reviewer → critic → Claude) → Commit
```

**Architecture change** (irreversible decision, auth, prod):
```
Brainstorm → Spec → Design (thinker) → Implement (builder) → Review (reviewer → critic → Claude) → /code-review ultra → Commit
```

## Fleet configuration modes

- **Recommended** — multi-provider, optimized cost/quality (default)
- **Full-stack Claude** — single Anthropic API key, haiku/sonnet/opus tiers
- **Custom** — each agent configured individually via `/trufagent:config`

## Git

- **User does:** branches (`git checkout -b`), push, pull, merge
- **Claude does:** `git add` (specific files, never `-A`) + `git commit`

## Security

- `reset --hard`, `branch -D`, drop table, `rm -rf` → explicit user confirmation required
- Changes to auth, `.env`, production config → explicit user confirmation required
- `writer` only touches `.md` files and commit messages, never source code
- No sub-agent makes commits — only Claude directly

## Session start

1. Read project `CLAUDE.md`
2. Read `docs/context/state.md`
3. If `docs/context/pending-updates.md` has content → propose `state.md` update before starting work
