---
description: Use this skill to initialize the trufagent context system in the current project directory — auto-detects the tech stack, asks 5-7 questions about project state, then generates CLAUDE.md and docs/context/ with real content. Run once per project. Invoke with /trufagent:init or when the user says "init trufagent", "initialize project context", or "setup project for trufagent".
---

# trufagent:init

Initializes the trufagent context system for the current project. Run from the project root directory.

## Phase A — Auto-detection (silent, no questions)

Read these files and extract information without asking anything:

```bash
cat package.json 2>/dev/null
cat prisma/schema.prisma 2>/dev/null | grep -E "^(model |datasource |enum )"
cat tsconfig.json 2>/dev/null
cat next.config.ts 2>/dev/null || cat next.config.js 2>/dev/null
cat middleware.ts 2>/dev/null | head -20
find app -name "page.tsx" -o -name "route.ts" 2>/dev/null | head -20
cat auth.ts 2>/dev/null | head -20
ls vitest.config.* jest.config.* playwright.config.* 2>/dev/null
git branch --show-current 2>/dev/null
```

Summarize findings before asking questions:
```
Detected: Next.js 16 + Prisma + PostgreSQL + NextAuth v5 + TypeScript
25 models in schema, 12 API routes, current branch: main
```

## Phase B — Interactive questions (one at a time, wait for each answer)

**Q1:** "Which features are fully complete and working?"

**Q2:** "What is currently in progress? (what were you working on before this session)"

**Q3:** "Are there any critical constraints I must know? (files not to touch without discussion, mandatory patterns, irreversible decisions already made)"

**Q4:** "What is the most important technical decision made in this project?"

**Q5 (only if external integrations detected):** "What is the current status of [detected integration]? (working, in development, or pending)"

**Q6 (optional):** "Are there any known issues or significant technical debt I should be aware of?"

## Phase C — Generate files

**CLAUDE.md** in project root:

```markdown
# [Project Name]

## Stack
[detected framework + exact versions]

## Dev server
[detected start command and port]

## Database
[detected DB type + key models]

## Auth
[detected auth setup]

## Conventions
[detected from code structure]

## Constraints
[from Q3 — critical constraints Claude must always respect]

## Commands
[from package.json scripts]
```

**docs/context/state.md**:

```markdown
# Project State — [today's date]

## Current branch
[from git or Q answer]

## Completed
[from Q1 — as checklist]

## In progress
[from Q2]

## Pending
[inferred or left blank]

## Known issues
[from Q6 or "None recorded"]
```

**docs/context/decisions/[date]-initial.md**:

```markdown
# Initial technical decisions
Date: [today]

## [Decision from Q4]
**Decision:** [what was decided]
**Why:** [reasoning]
**Consequences:** [implications]
```

```bash
mkdir -p docs/context/decisions/technical
mkdir -p docs/context/decisions/lessons
mkdir -p docs/context/decisions/preferences
mkdir -p docs/context/decisions/goals
touch docs/context/pending-updates.md
```

**decisions/ categories:**
- `technical/` — stack choices, architecture, tools selected
- `lessons/` — mistakes made and what was learned (avoid repeating)
- `preferences/` — how the team likes to work (naming, patterns, style)
- `goals/` — long-term project objectives

Write the Q4 answer as `docs/context/decisions/technical/[date]-initial.md`.

## Final output

Print:

```
Context system initialized.

  CLAUDE.md                                       created
  docs/context/state.md                           created
  docs/context/decisions/technical/[date]-initial created
  docs/context/decisions/lessons/                 ready
  docs/context/decisions/preferences/             ready
  docs/context/decisions/goals/                   ready
  docs/context/pending-updates.md                 created

At the start of each session, these files will be read automatically.
If commits happened between sessions, I will propose updating state.md before starting work.
```

Then open the dashboard so the user can verify or complete fleet configuration:

```
Opening trufagent dashboard…
```

Execute dashboard launch inline:

1. Check if server already running: read `~/.trufagent/ui.pid`, test with `kill -0 $PID 2>/dev/null`
2. If not running, find server path:
   ```bash
   UI_DIR="$(find ~/.claude -name 'server.py' -path '*/trufagent/ui/*' 2>/dev/null | head -1 | xargs dirname)"
   ```
   If `UI_DIR` is empty, skip dashboard launch and tell the user: "Run /trufagent:setup first to install the dashboard."
3. Launch server:
   ```bash
   python3 "$UI_DIR/server.py" &
   ```
4. Wait up to 15 × 0.3s for it to respond:
   ```bash
   for i in $(seq 1 15); do sleep 0.3; curl -sf http://localhost:7433 > /dev/null 2>&1 && break; done
   ```
5. Open browser:
   ```bash
   xdg-open http://localhost:7433 2>/dev/null || open http://localhost:7433 2>/dev/null || echo "Open http://localhost:7433 in your browser"
   ```
