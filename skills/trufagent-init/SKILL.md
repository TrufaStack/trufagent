---
name: trufagent-init
description: Run in a project directory to initialize the trufagent context system — auto-detects the stack, asks 5-7 questions about project state, then generates CLAUDE.md and docs/context/ with real content. Run once per project.
triggers:
  - /trufagent init
  - initialize trufagent
  - init trufagent context
---

# trufagent-init

Initializes the trufagent context system for the current project. Generates `CLAUDE.md` and `docs/context/` with real content — not empty templates.

Run from the project root directory.

## What this skill does

**Phase A — Auto-detection** (no questions, reads files silently):
- Detects stack, versions, DB, auth, testing setup
- Detects existing routes, components, API endpoints

**Phase B — Interactive questions** (5-7 questions, one at a time):
- Project state, pending features, critical constraints, key decisions, known issues

**Phase C — Generate files**:
- `CLAUDE.md` with detected stack + answered constraints
- `docs/context/state.md` with current project state
- `docs/context/decisions/YYYY-MM-DD-initial.md` with key decisions
- `docs/context/pending-updates.md` (empty, ready for hooks)

## Execution

### Phase A — Auto-detect stack

Read these files silently and extract info:

**package.json** → framework, key dependencies, scripts
```bash
cat package.json 2>/dev/null
```

**prisma/schema.prisma** → DB provider, model list, complexity
```bash
cat prisma/schema.prisma 2>/dev/null | grep -E "^(model |datasource |enum )"
```

**tsconfig.json** → TypeScript strictness, paths
```bash
cat tsconfig.json 2>/dev/null
```

**next.config.ts or next.config.js** → Next.js features
```bash
cat next.config.ts 2>/dev/null || cat next.config.js 2>/dev/null
```

**middleware.ts** → Protected routes, auth patterns
```bash
cat middleware.ts 2>/dev/null
```

**app/ or pages/ structure** → Routes, pages
```bash
find app -name "page.tsx" -o -name "route.ts" 2>/dev/null | head -20
```

**auth.ts or auth.config.ts** → Auth provider
```bash
cat auth.ts 2>/dev/null | head -20
```

**Test setup** → vitest, jest, playwright
```bash
ls vitest.config.* jest.config.* playwright.config.* 2>/dev/null
```

### Phase B — Questions (one at a time, wait for answer before next)

After auto-detection, summarize what was found, then ask:

**Q1:** "¿Qué features están completamente terminadas y funcionando en producción o listas para deploy?"

**Q2:** "¿Qué está en progreso ahora mismo? (lo que estabas trabajando antes de esta sesión)"

**Q3:** "¿Hay restricciones críticas que debo conocer? Por ejemplo: archivos que no debo tocar sin discutir, patrones que debemos seguir obligatoriamente, decisiones irreversibles ya tomadas."

**Q4:** "¿Cuál es la decisión técnica más importante que tomaste en este proyecto? (la que más impacto tiene en el código)"

**Q5 (condicional — solo si hay integraciones externas detectadas):** "¿Cuál es el estado actual de [integración detectada]? ¿Está funcionando, en desarrollo, o pendiente?"

**Q6 (opcional):** "¿Hay issues conocidos o deuda técnica importante que deba tener en cuenta?"

### Phase C — Generate files

**Generate CLAUDE.md** in project root:

```markdown
# [Project Name]

## Stack
[detected framework + versions]

## Dev server
[detected start command and port]

## Database
[detected DB type, provider, key models list]

## Auth
[detected auth setup]

## Convenciones
[detected patterns from code structure]

## Restricciones
[from Q3 answers]

## Comandos clave
[from package.json scripts]
```

**Generate docs/context/state.md**:

```markdown
# Estado del Proyecto — [today's date]

## Rama actual de trabajo
[ask or detect from git branch --show-current]

## Completado
[from Q1 answers, formatted as checklist]

## En progreso
[from Q2 answers]

## Pendiente
[features not mentioned as done or in progress, from project docs if available]

## Issues conocidos
[from Q6 answers, or "Ninguno registrado"]
```

**Generate docs/context/decisions/[date]-initial.md**:

```markdown
# Decisiones técnicas iniciales
Fecha: [today]

## Contexto
Setup inicial del sistema de contexto trufagent para este proyecto.

## Decisiones clave
[from Q4 and Q3 answers, one section per decision]

## [Decision name]
**Decisión:** [what was decided]
**Por qué:** [reasoning from user's answer]
**Consecuencias:** [implications]
```

**Create docs/context/pending-updates.md** (empty):
```bash
touch docs/context/pending-updates.md
```

### Final output

```
✓ CLAUDE.md generado
✓ docs/context/state.md generado
✓ docs/context/decisions/[date]-initial.md generado
✓ docs/context/pending-updates.md creado

El sistema de contexto está activo. En la próxima sesión:
→ Leeré CLAUDE.md + state.md automáticamente
→ Si hay commits entre sesiones, propondré actualizar state.md
```
