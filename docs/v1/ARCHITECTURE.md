# Trufagent v1 — Architecture

Estado: arquitectura inicial implementable  
Fecha: 2026-07-30

## 1. Objetivo

Construir un core local y portable que:

1. recupere conocimiento gobernado;
2. consulte la cartografía de Graphify;
3. clasifique exploración, ejecución y verificación;
4. seleccione skills confiables;
5. produzca un plan abstracto y auditable;
6. delegue la ejecución a adaptadores de plataforma.

La primera línea vertical termina al mostrar una estrategia. No modifica código
ni llama modelos automáticamente.

## 2. Principios arquitectónicos

- Core independiente de Claude Code, Codex y LiteLLM.
- Memoria canónica legible; índices y grafos derivados.
- Graphify obligatorio detrás de un adaptador.
- Entradas y salidas tipadas en límites.
- Planificación flexible; acciones deterministas.
- Reglas críticas evaluadas antes de herramientas.
- Errores con causa, retry seguro y condición de parada.
- Contexto referenciado y presupuestado, no concatenado indiscriminadamente.
- Dependencias dirigidas hacia contratos del core.

## 3. Vista general

```text
CLI / adapter de plataforma
          │
          ▼
   Application service
          │
   ┌──────┼────────┬──────────┐
   ▼      ▼        ▼          ▼
Memory  Policy   Skills   Cartography port
   │      │        │          │
   ▼      ▼        ▼          ▼
Markdown Rules   Catalog   Graphify adapter
SQLite   Casebook Profiles  CLI + MCP
```

## 4. Capas

### 4.1 Domain

Modelos sin acceso a filesystem, red o procesos:

- memoria y ciclo de vida;
- perfil de tarea;
- presupuestos de esfuerzo;
- paquetes de contexto;
- selección de skills;
- observaciones y errores;
- estado de cartografía.

### 4.2 Application

Casos de uso:

```text
plan_task
recall_context
propose_memory
review_memory
validate_project
refresh_cartography
```

Coordina puertos; no conoce formatos de Graphify ni detalles de plataforma.

### 4.3 Ports

Interfaces del core:

```text
MemoryRepository
MemoryIndex
CartographyPort
SkillCatalog
PolicyEngine
PlatformAdapter
AuditSink
```

### 4.4 Infrastructure

Implementaciones:

- documentos Markdown + YAML;
- índice SQLite FTS5;
- Graphify CLI/MCP;
- filesystem y Git;
- configuración local;
- observabilidad.

### 4.5 Interfaces

- CLI `trufagent`;
- adaptador Claude Code;
- adaptador Codex;
- dashboard futuro.

## 5. Paquetes Python

```text
src/trufagent/
├── __init__.py
├── cli.py
├── domain/
│   ├── cartography.py
│   ├── context.py
│   ├── memory.py
│   ├── observation.py
│   ├── session.py
│   ├── skills.py
│   └── task.py
├── application/
│   ├── context_builder.py
│   ├── errors.py
│   ├── memory_review.py
│   ├── plan_task.py
│   ├── ports.py
│   ├── prepare_task.py
│   ├── sessions.py
│   ├── skill_catalog.py
│   └── task_classifier.py
└── infrastructure/
    ├── graphify_adapter.py
    ├── memory_fs.py
    ├── memory_index.py
    └── memory_markdown.py
```

La infraestructura incluye además `project_init.py`, `session_fs.py`,
`skill_catalog_fs.py` y `skill_discovery.py`.

El núcleo implementa modelos, parsing, vault filesystem, índice FTS5 derivado,
adaptador CLI de Graphify y paquetes de contexto presupuestados. Los servicios
de clasificación determinista ya producen perfiles y presupuestos explicables;
la orquestación completa se añade después de estabilizar sus fixtures.

La clasificación no interpreta lenguaje natural. Consume `TaskSignals`
tipadas, aplica una base por clase de tarea y luego escaladores independientes
para secretos, producción, persistencia, permisos, contratos compartidos,
artefactos y evidencia visual. Cada cambio conserva una razón auditable.

`PlanTaskService` compone la primera línea vertical:

```text
TaskSignals
→ classify_task
→ ContextBuilder (memory + Graphify)
→ SkillCatalog
→ TaskPlan
```

La ausencia de Graphify se degrada con advertencia en una tarea trivial. Para
arquitectura, persistencia, contratos compartidos o múltiples superficies,
convierte la frontera de autonomía en `block` hasta refrescar la cartografía.

El catálogo activa únicamente skills presentes y revisadas. Las exclusiones
explícitas tienen precedencia sobre sugerencias y selecciones forzadas.

El catálogo personal vive en `~/.trufagent/skills/catalog.yaml`. Discovery
combina roots de Claude, Codex y plugins activos mediante fingerprints. Un
cambio de contenido revoca revisión; conflictos de nombre quedan inactivos
hasta elegir variante.

Cada proyecto enlaza el catálogo desde `.trufagent/config.yaml`, creado mediante
`trufagent init`. La configuración es create-only y no contiene secretos.

El ciclo de sesión usa `.trufagent/state/`, completamente ignorado. Start
recupera solo el handoff más reciente; end escribe journal y puede proponer
memoria `proposed/unreviewed`, sin commits ni promoción automática.

La revisión de memoria se registra como eventos create-only adyacentes al scope.
El repositorio materializa el estado efectivo al leer y falla cerrado ante una
cadena inconsistente. Aceptar, rechazar o superseder reconstruye el índice FTS5;
ninguna transición modifica el Markdown original.

`task_extractor.py` propone señales desde texto mediante reglas locales y
auditables. `PrepareTaskService` detiene el flujo ante preguntas bloqueantes o
entrega las señales visibles a `PlanTaskService`; no existe una segunda política
de clasificación dentro del extractor.

## 6. Flujo `plan_task`

```text
1. Normalizar solicitud y proyecto.
2. Cargar reglas críticas aplicables.
3. Comprobar estado de Graphify.
4. Consultar símbolos y relaciones relevantes.
5. Recuperar decisiones, riesgos y artefactos vinculados.
6. Resolver conflictos de autoridad.
7. Clasificar tarea y presupuestos.
8. Seleccionar conjunto mínimo de skills.
9. Definir evidencia requerida.
10. Emitir estrategia tipada y resumen humano.
```

La regla de secretos se evalúa en el paso 2. No depende del grafo.

## 7. Action space

Herramientas del core previstas:

```text
memory_search
memory_read
memory_propose
memory_review
memory_validate

cartography_status
cartography_update
cartography_query
cartography_path
cartography_affected

skills_search
skills_select

policy_classify
plan_build
```

No habrá una herramienta genérica `execute_anything`.

Operaciones de alto riesgo —shell, producción, permisos— permanecen en
adaptadores con gates específicos.

## 8. Contrato de observación

Toda operación devuelve:

```yaml
status: success | warning | error
summary: resultado en una línea
next_actions: []
artifacts: []
error:
  code: null
  root_cause_hint: null
  safe_retry: null
  stop_condition: null
```

Los artefactos son rutas o IDs, nunca blobs grandes.

## 9. Memoria

Fuente:

```text
.trufagent/memory/project/
.trufagent/memory/team/
~/.trufagent/memory/user/
```

Pipeline:

```text
Markdown/YAML
→ parser seguro
→ detección de secretos
→ modelo Pydantic
→ validación de ciclo de vida
→ índice SQLite derivado
→ context packet con presupuesto y autoridad explícita
```

El índice puede eliminarse y reconstruirse. Los documentos permanecen
canónicos.

La recuperación ordinaria incluye `project` y `team`. El scope `user` requiere
opt-in explícito en cada solicitud. Entradas `rejected`, `superseded` o `stale`
no aparecen en recuperación ordinaria; una entrada no revisada puede informar,
pero el paquete la marca como no gobernante y no confiable.

## 10. Cartografía

Graphify se consume mediante `CartographyPort`. La implementación:

- usa MCP para consultas interactivas cuando está disponible;
- usa CLI para build, update, affected y fallback;
- comprueba commit y worktree;
- nunca promueve memoria;
- traduce resultados a modelos internos.

Detalles: [`GRAPHIFY-ADAPTER.md`](./GRAPHIFY-ADAPTER.md).

## 11. Skills

El catálogo separa:

- biblioteca instalada;
- perfil personal activo;
- perfil del proyecto;
- selección de tarea.

La selección se basa en metadatos resumidos. El cuerpo completo de una skill se
carga solamente después de seleccionarla.

## 12. Configuración

Orden de precedencia:

```text
flags de la operación
→ .trufagent/config.yaml
→ ~/.trufagent/config.yaml
→ defaults seguros
```

Variables de entorno se reservan para secretos o integración de procesos. No se
imprimen sus valores.

## 13. Seguridad

- Roots normalizados y aprobados.
- No seguir symlinks fuera del proyecto.
- Escrituras create-only o atómicas.
- Scanner de formas conocidas de secretos.
- Contenido recuperado tratado como datos.
- Ninguna memoria eleva permisos.
- Comandos de shell creados por adaptadores especializados.
- Confirmaciones por acción; no permisos permanentes implícitos.

## 14. Errores y recuperación

| Error | Retry seguro | Stop condition |
|---|---|---|
| YAML inválido | corregir documento propuesto | memoria aceptada corrupta |
| secreto detectado | redactar y volver a proponer | no existe versión segura |
| grafo stale | `graphify update .` | actualización incompleta |
| MCP caído | fallback CLI | CLI ausente o corrupta |
| índice SQLite corrupto | reconstruir desde Markdown | documentos canónicos inválidos |
| conflicto de decisiones | solicitar revisión humana | nunca escoger silenciosamente |

## 15. Observabilidad

Registrar metadatos operativos:

- tipo de operación;
- IDs y rutas no sensibles;
- duración;
- status;
- presupuesto;
- versión de adaptadores;
- artefactos producidos.

No registrar:

- secretos;
- transcripciones completas;
- razonamiento privado;
- outputs de herramientas sin filtrar.

## 16. Distribución

Según [ADR-0005](../adr/0005-build-core-in-python-with-uv.md):

- Python 3.12;
- uv y lockfile;
- paquete `src/`;
- comando `trufagent`;
- Graphify como dependencia encapsulada;
- dashboard fuera del runtime mínimo.

## 17. Fases

### Fase 1 — Contratos

- modelos Pydantic;
- parser Markdown/YAML;
- scanner inicial de secretos;
- respuestas tipadas;
- puertos;
- fixtures C02, C05, C09 y C10.

### Fase 2 — Recuperación

- repositorio filesystem;
- SQLite FTS5;
- ranking y paquetes de contexto;
- tests de contaminación.

### Fase 3 — Graphify

- status/update/query/affected;
- MCP con fallback CLI;
- frescura y degradación;
- relaciones memoria-símbolo.

### Fase 4 — Política y skills

- clasificación de presupuestos;
- catálogo;
- selección mínima;
- evaluación contra Casebook.

### Fase 5 — Plataformas

- adaptador de referencia;
- Claude Code y Codex;
- ejecución tipada y gates.

## 18. Criterio para avanzar

Fase 1 termina cuando:

- los modelos generan JSON Schema;
- entradas válidas de C02, C05, C09 y C10 cargan;
- una forma de secreto se rechaza;
- una propuesta no gobierna;
- una regla aceptada y revisada sí gobierna;
- todas las operaciones usan el contrato de observación;
- la suite corre en entorno uv bloqueado.
