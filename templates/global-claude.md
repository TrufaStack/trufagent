# trufagent — Framework Global

## Fleet de Agentes

| Agente | Modelo | Cuándo usarlo |
|--------|--------|---------------|
| `scout` | gemini-flash | Exploración: leer archivos, grep, listar directorios, parsear |
| `runner` | groq-llama | Velocidad: tareas paralelas independientes, conversiones rápidas |
| `thinker` | deepseek-v3 | Razonamiento profundo: debugging, algoritmos, arquitectura, 1er review |
| `builder` | qwen-coder | Implementación: componentes, APIs, CRUD, features completas |
| `writer` | mistral-free | Texto no crítico: commit messages, changelogs |
| `critic` | claude-opus-4-8 | Review profundo: arquitectura, seguridad, decisiones irreversibles [opcional] |

**Orquestador:** Claude Sonnet — toma decisiones de delegación, maneja contexto completo, segunda pasada de review, escribe commits, documentación importante.

## Delegación

Siempre anuncio antes de delegar:
> `→ delegando a [agente] porque [razón]`

## Workflow

**Cambio simple** (1 archivo, sin DB, sin nueva ruta):
```
Implement → Review (thinker → Claude) → Commit
```

**Feature nueva** (migración DB, integración externa, múltiples módulos):
```
Brainstorm → Spec → Implement → Review (thinker → critic → Claude) → Commit
```

**Arquitectura mayor** (decisión irreversible, auth, prod):
```
Brainstorm → Spec → Implement → Review (thinker → critic → Claude) → /code-review ultra → Commit
```

## Git

- **Usuario hace:** branches (`git checkout -b`), push, pull, merge
- **Claude hace:** `git add` (archivos específicos, nunca `-A`) + `git commit`

## Seguridad

- `reset --hard`, `branch -D`, drop table, `rm -rf` → confirmación explícita del usuario
- Cambios en auth, `.env`, configuración de producción → confirmación explícita del usuario
- `writer` solo toca `.md` y mensajes de commit, nunca código fuente
- Ningún sub-agente hace commits — solo Claude directamente

## Inicio de cada sesión

1. Leer `CLAUDE.md` del proyecto activo
2. Leer `docs/context/state.md`
3. Si `docs/context/pending-updates.md` tiene contenido → proponer actualización de `state.md` antes de empezar
