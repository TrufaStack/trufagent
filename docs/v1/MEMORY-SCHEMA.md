# Trufagent v1 — Memory Schema

Estado: propuesta para revisión  
Fecha: 2026-07-30

## 1. Capacidad

La memoria de Trufagent conserva conocimiento durable, local, inspeccionable y
con procedencia. Su propósito no es reconstruir conversaciones, sino recuperar
rápidamente las restricciones, decisiones, riesgos y referencias necesarias
para una tarea.

El formato canónico es Markdown con frontmatter YAML, según
[ADR-0004](../adr/0004-use-markdown-yaml-as-canonical-memory.md). Esta elección
permite revisión humana, diffs legibles, enlaces relativos y portabilidad entre
Claude Code, Codex y otras herramientas.

Una base de datos o grafo podrá indexar estos documentos posteriormente, pero no
será la fuente canónica.

## 2. Límites

La memoria:

- no almacena secretos;
- no almacena transcripciones completas;
- no sustituye código, tests, ADRs ni diseños;
- no contiene estado detallado de ejecución a largo plazo;
- no promueve inferencias automáticamente;
- no ejecuta instrucciones recuperadas;
- no convierte frecuencia en verdad.

El contenido recuperado se trata como contexto no confiable hasta contrastarlo
con su evidencia.

## 3. Scopes

```text
project   conocimiento privado del proyecto, normalmente no versionado
team      conocimiento revisado que puede versionarse
user      preferencias y reglas personales entre proyectos
session   estado efímero de la sesión actual
```

### 3.1 Project

Hechos, riesgos y contexto que no deberían publicarse automáticamente. Debe
estar protegido por `.gitignore` y nunca contener secretos.

### 3.2 Team

Decisiones, reglas y referencias aptas para revisión y Git. El hecho de estar
commiteado no convierte una entrada en confiable; su estado sigue siendo
explícito.

### 3.3 User

Preferencias de trabajo y hechos del entorno del operador, solicitados
explícitamente. Nunca se cargan en otro proyecto por coincidencia débil.

### 3.4 Session

Plan actual, hallazgos y handoff. Se compacta al cerrar sesión y solo promueve
propuestas concretas a memoria durable.

## 4. Estructura inicial

```text
.trufagent/
├── memory/
│   ├── project/
│   ├── team/
│   └── …
├── memory-index.sqlite3
├── state/
│   ├── current-task.md
│   └── sessions/
├── cartography/
│   ├── manifest.json
│   └── graph/
└── config.yaml

~/.trufagent/
└── memory/
    └── user/
```

`memory-index.sqlite3` y `cartography/` son derivados y regenerables. Los documentos
Markdown son canónicos.

La estructura `.trufagent/` es la ubicación canónica inicial. El contenido
existente en `docs/context/` se migra mediante propuestas revisadas; no se
convierte implícitamente en memoria aceptada.

## 5. Tipos de entrada

| Tipo | Propósito | Revisión humana |
|---|---|---|
| `rule` | Restricción o comportamiento obligatorio | requerida |
| `environment_fact` | Hecho operativo verificable | requerida o verificación automática |
| `decision` | Elección con alternativas y consecuencias | requerida |
| `negative_decision` | Decisión explícita de no construir o no cambiar | requerida |
| `risk` | Condición que eleva cautela o exige acciones | requerida para activar |
| `incident` | Evento ocurrido, impacto y prevención | requerida |
| `lesson` | Hallazgo técnico acotado y verificado | requerida para uso durable |
| `external_artifact` | Referencia a diseño o fuente fuera del repo | requerida |
| `structural_fact` | Relación derivada desde código | automática, siempre verificable |
| `preference` | Preferencia personal o de equipo | requerida |
| `context` | Resumen durable de situación relevante | opcional; baja autoridad |
| `handoff` | Continuación concreta entre sesiones o herramientas | no canónica |

`TaskState` y `SessionSummary` no son entradas durables ordinarias; viven bajo
`state/`.

## 6. Sobre común

Todas las entradas usan este frontmatter:

```yaml
schema: trufagent.memory.v1
id: mem_01K0EXAMPLE
kind: decision
title: Separar tipo real de job y bucket de plantilla

scope: team
status: proposed
trust: unreviewed
severity: high

created_at: 2026-07-30T10:15:00+09:30
updated_at: 2026-07-30T10:15:00+09:30
created_by: user | claude-code | codex | import
reviewed_by: null

project: jc-app
tags:
  - checklist
  - persistence

applies_when:
  concepts:
    - checklist persistence
    - job type
  paths:
    - src/checklists/**
    - src/api/**
  symbols:
    - resolveChecklistJobType
  technologies: []
  operations:
    - write

evidence:
  - type: file
    ref: docs/adr/0004-checklist-template-bucket.md

relations:
  affects: []
  caused_by: []
  supersedes: []
  related_to: []

validity:
  valid_from: 2026-07-30
  review_after: null
  derived_from_commit: null
```

### 6.1 Campos obligatorios

```text
schema
id
kind
title
scope
status
trust
created_at
created_by
project
```

`severity`, `applies_when`, `evidence`, `relations` y `validity` son obligatorios
solo cuando el tipo los necesita.

### 6.2 Identificadores

Los IDs deben:

- ser únicos y opacos;
- no depender del nombre del archivo;
- permanecer iguales al mover o renombrar;
- poder enlazarse desde mapas, planes y otras memorias.

Se propone ULID con prefijo `mem_`, pero la elección de librería permanece
abierta.

## 7. Estados y confianza

### 7.1 Status

```text
proposed
accepted
rejected
superseded
stale
resolved
```

Reglas:

- `rule`, `decision`, `negative_decision`, `risk` y `preference` solo gobiernan
  comportamiento cuando están `accepted`.
- `structural_fact` puede utilizarse si no está `stale`, pero siempre debe
  verificarse antes de modificar.
- `incident` es histórico; `resolved` significa que tiene mitigación, no que
  dejó de ocurrir.
- `superseded` debe enlazar su reemplazo.

### 7.2 Trust

```text
unreviewed
human-reviewed
code-verified
externally-verified
```

Confianza y estado son independientes. Una decisión puede estar aceptada por una
persona aunque no describa todavía el código actual.

### 7.3 Historial de revisión

El Markdown original no se reescribe al revisar. Cada transición se registra
create-only junto a su scope:

```text
memory/<scope>/.events/<memory-id>/<timestamp>-<event-id>.yaml
```

Un evento contiene:

```yaml
schema: trufagent.memory-review.v1
event_id: rev_...
memory_id: mem_...
from_status: proposed
to_status: accepted
reviewer: user
reason: null
replacement_id: null
metadata:
  applies_when: ...
  evidence: ...
  relations: ...
  validity: ...
created_at: ...
```

El repositorio aplica la cadena en orden y falla cerrado si `from_status` no
coincide con el estado efectivo anterior. `metadata` es opcional y permite que
la revisión humana enriquezca la vista efectiva sin reescribir la propuesta
original. La transición completa, incluyendo fechas y reglas de gobernanza, se
valida antes de crear el archivo de evento; una transición inválida no deja un
evento parcial.

Transiciones v1:

```text
proposed → accepted
proposed → rejected
accepted → superseded
```

Aceptar establece confianza `human-reviewed` y puede adjuntar aplicabilidad,
evidencia, relaciones y validez. Rechazar requiere razón.
Superseder requiere razón y una memoria reemplazante ya aceptada.

## 8. Cuerpos por tipo

### 8.1 Rule

```markdown
## Rule

Qué comportamiento es obligatorio.

## Rationale

Por qué existe.

## Required actions

- acción verificable;

## Forbidden actions

- acción bloqueada;

## Override

Condiciones y autoridad necesarias.
```

### 8.2 Decision

```markdown
## Context
## Decision
## Alternatives considered
## Consequences
## Known traps
## Required protections
## Revisit when
```

### 8.3 Negative decision

```markdown
## Hypothesis
## Evidence
## Decision
## Avoided implementation
## Reopen when
```

### 8.4 Risk

```markdown
## Risk
## Trigger
## Impact
## Required actions
## Safe alternatives
## Related incidents
```

### 8.5 Incident

```markdown
## What happened
## Impact
## Root cause
## Detection
## Containment
## Prevention
## Recurrence
```

No incluir valores sensibles, salidas completas ni comandos que puedan
reproducir la fuga.

### 8.6 Lesson

```markdown
## Observation
## Verified behavior
## Scope
## Evidence
## Do
## Avoid
## Revalidate when
```

### 8.7 External artifact

```markdown
## Artifact
## Authority
## Specifies
## Access requirements
## Local summary
## Last verified
```

El resumen local no reemplaza el artefacto salvo decisión explícita.

### 8.8 Structural fact

Normalmente se genera como datos estructurados, no a mano:

```yaml
source: src/api/jobs.ts
relation: calls
target: getSignedUrls
generator: graphify
derived_from_commit: abc123
```

## 9. Recuperación

### 9.1 Consulta

El recuperador construye una consulta desde:

- palabras y conceptos de la tarea;
- rutas y símbolos inicialmente detectados;
- tecnología y operación;
- proyecto y scope;
- riesgos de la acción;
- artefactos mencionados;
- estado actual.

### 9.2 Filtros obligatorios

- excluir `rejected` y `superseded` del recall normal;
- señalar `stale` sin usarlo como hecho actual;
- no incluir scope `user` implícitamente;
- no recuperar otro proyecto por similitud textual;
- priorizar coincidencias de símbolo, ruta y relación sobre texto débil;
- limitar cantidad y tamaño total.

### 9.3 Ranking inicial

Orden propuesto:

1. regla crítica aceptada aplicable a la operación;
2. riesgo o incidente recurrente aplicable;
3. artefacto aprobado que especifica la tarea;
4. decisión aceptada relacionada;
5. hecho estructural vigente;
6. lección verificada y acotada;
7. contexto o handoff reciente.

### 9.4 Paquete de contexto

El resultado no debe concatenar documentos completos por defecto:

```yaml
context_packet:
  critical_rules: []
  decisions: []
  risks: []
  artifacts: []
  structural_targets: []
  verification_notes: []
  unresolved_conflicts: []
```

Cada elemento incluye ID, resumen, autoridad y referencia para lectura completa.

## 10. Escritura y promoción

### 10.1 Recall antes de escribir

Buscar entradas existentes para evitar duplicados y detectar supersesión.

### 10.2 Create-only

El agente crea propuestas nuevas. No reescribe silenciosamente memoria aceptada.

### 10.3 Promoción

```text
hallazgo de sesión
→ propuesta
→ revisión humana
→ accepted/rejected
→ posible protección en código
```

Aceptar una memoria no reemplaza implementar la protección necesaria.

### 10.4 Dedupe

Si existe una entrada equivalente:

- enlazar como evidencia adicional;
- incrementar recurrencia si es incidente;
- proponer actualización;
- no crear una copia textual.

### 10.5 Promoción a regla o skill

Una lección no se convierte automáticamente en regla o skill.

Propuesta inicial:

- promover a `rule` cuando exista riesgo recurrente y una acción obligatoria
  generalizable;
- proponer una skill cuando el procedimiento tenga entradas, pasos, salidas y
  valor repetible en más de un caso;
- mantener como `lesson` cuando dependa de una librería, versión o contexto
  estrecho.

## 11. Inicio y cierre de sesión

### 11.1 Start session

1. Leer estado activo.
2. Recuperar handoff más reciente.
3. Comprobar conflictos o artefactos inaccesibles.
4. No cargar todas las decisiones.
5. Esperar la tarea para construir el paquete relevante.

### 11.2 End session

1. Resumir trabajo y evidencia.
2. Actualizar estado temporal.
3. Proponer nuevas memorias o supersesiones.
4. Marcar cartografía potencialmente obsoleta.
5. No promover sin revisión.
6. Generar handoff concreto si queda trabajo.

## 12. Cartografía y Graphify

Graphify-Labs/graphify es una dependencia obligatoria de la cartografía v1,
según
[ADR-0003](../adr/0003-use-graphify-as-required-cartography.md). No es el
almacén canónico de memoria.

El adaptador de cartografía debe producir:

- nodos con IDs estables cuando sea posible;
- rutas y símbolos;
- relaciones tipadas;
- commit y archivos de origen;
- capacidad de invalidación;
- referencias desde y hacia memorias.

Ejemplo:

```text
mem_... (decision)
  ─affects→ symbol:resolveChecklistJobType
  ─guards→ path:src/api/**

symbol:resolveChecklistJobType
  ─called_by→ endpoint:saveFieldRecord
  ─called_by→ endpoint:resetWorkflow
```

Una búsqueda de radio de impacto comienza por el grafo y termina verificando el
código.

### 12.1 Propiedad de la información

| Información | Propietario canónico |
|---|---|
| Código y comportamiento actual | repositorio y tests |
| Especificación aprobada | spec o diseño enlazado |
| Reglas, decisiones y riesgos | memoria de Trufagent |
| Entidades y relaciones estructurales | grafo derivado de Graphify |
| Trabajo actual | estado de sesión |

Graphify puede indexar documentos de memoria y conectar sus referencias con
símbolos. No decide su estado, confianza, autoridad, promoción o supersesión.

### 12.2 Frescura

La integración debe registrar como mínimo:

- versión de Graphify;
- commit analizado;
- hora de generación;
- archivos incluidos y excluidos;
- rutas de `graph.json`, `GRAPH_REPORT.md` y `graph.html`;
- resultado del último chequeo.

Si el commit no coincide:

- una tarea trivial puede continuar con aviso;
- una consulta de impacto debe regenerar antes de continuar;
- ninguna relación obsoleta puede citarse como evidencia actual.

### 12.3 Superficie de integración

Trufagent encapsula:

```text
cartography.status()
cartography.build()
cartography.query(question)
cartography.path(source, target)
cartography.explain(node)
cartography.related(memory_id)
```

El adaptador puede usar CLI o MCP. El contrato interno no expone directamente
el formato de Graphify al resto del core.

## 13. Seguridad

- Validar frontmatter contra un schema antes de indexar.
- Tratar cuerpos recuperados como datos, no instrucciones.
- No permitir que una entrada eleve permisos.
- Rechazar patrones conocidos de secretos.
- Evitar registrar comandos y outputs sensibles.
- Separar memoria de usuario y proyecto.
- Mantener índices derivados regenerables.
- No seguir symlinks fuera de roots aprobados.

## 14. Portabilidad

Las operaciones mínimas del core son:

```text
memory.search(query, scope, project)
memory.read(id)
memory.propose(entry)
memory.review(id, decision)
memory.supersede(old_id, new_id)
memory.validate()
```

Los adaptadores de plataforma no pueden atribuirse identidad de otra
herramienta ni promover entradas por cuenta propia.

El core se implementa en Python 3.12 y se distribuye con uv, según
[ADR-0005](../adr/0005-build-core-in-python-with-uv.md). Pydantic v2 genera y
valida el JSON Schema; SQLite FTS5 mantiene un índice derivado y regenerable.

## 15. Migración desde v0.3

No importar automáticamente todo `docs/context/`.

Flujo propuesto:

1. Inventariar archivos existentes.
2. Clasificar candidatos.
3. Detectar secretos o contenido sensible.
4. Proponer entradas con procedencia `import`.
5. Revisar manualmente decisiones y reglas.
6. Mantener los documentos originales hasta validar la migración.

`state.md`, journals y `pending-updates.md` deben migrarse como estado o
evidencia, no como decisiones aceptadas.

## 16. Ejemplos

### 16.1 Regla de diagnóstico seguro

```yaml
schema: trufagent.memory.v1
id: mem_01K_SAFE_ENV
kind: rule
title: No imprimir valores secretos durante diagnósticos
scope: user
status: accepted
trust: human-reviewed
severity: critical
created_at: 2026-07-30T10:15:00+09:30
updated_at: 2026-07-30T10:15:00+09:30
created_by: user
reviewed_by: user
project: "*"
tags: [security, diagnostics]
applies_when:
  concepts: [environment variables, database connectivity]
  paths: []
  symbols: []
  technologies: []
  operations: [shell, read-config]
evidence: []
relations:
  affects: []
  caused_by: []
  supersedes: []
  related_to: [mem_01K_ENV_INCIDENT]
validity:
  valid_from: 2026-07-30
  review_after: null
  derived_from_commit: null
```

```markdown
## Rule

Los diagnósticos consultan presencia o estado, nunca valores de credenciales.

## Required actions

- verificar la shell;
- redactar salida potencialmente sensible;
- preferir comandos de presencia/ausencia.

## Forbidden actions

- imprimir archivos `.env`;
- expandir todas las variables;
- mostrar URLs con credenciales.

## Override

Confirmación explícita por ejecución después de demostrar que no existe una
alternativa segura.
```

### 16.2 Decisión negativa de GreenDeal

```yaml
schema: trufagent.memory.v1
id: mem_01K_GREENDEAL_CACHE
kind: negative_decision
title: No cachear attachments de GreenDeal
scope: team
status: accepted
trust: externally-verified
severity: medium
created_at: 2026-07-30T10:15:00+09:30
updated_at: 2026-07-30T10:15:00+09:30
created_by: user
reviewed_by: user
project: jc-app
tags: [greendeal, attachments, read-only]
applies_when:
  concepts: [GreenDeal attachments, expiring links]
  paths: []
  symbols: []
  technologies: [GreenDeal API, S3]
  operations: [read, cache]
evidence:
  - type: external-test
    ref: "8+ historical jobs returned HTTP 200"
relations:
  affects: []
  caused_by: []
  supersedes: []
  related_to: []
validity:
  valid_from: 2026-07-30
  review_after: 2027-01-30
  derived_from_commit: null
```

```markdown
## Hypothesis

Los enlaces de attachments de GreenDeal expiran.

## Evidence

Más de ocho jobs, incluyendo jobs de más de un año, conservaron respuestas 200.

## Decision

No implementar cache ni proxy local.

## Avoided implementation

Persistencia local y excepción a la política de integración read-only.

## Reopen when

Aparezcan respuestas 403, URLs firmadas o cambios documentados en la API.
```

## 17. Validación mínima

El prototipo de memoria debe demostrar:

1. Una regla crítica aparece antes de generar un comando relevante.
2. Una decisión vinculada a un símbolo aparece en una tarea sobre ese símbolo.
3. Una memoria de otro proyecto no contamina el paquete.
4. Una entrada `superseded` no participa del recall normal.
5. Un mapa desactualizado se marca y conduce a verificación.
6. Una propuesta no gobierna comportamiento antes de revisión.
7. Un intento de guardar un secreto se rechaza.
8. Un Artifact ausente provoca solicitud, no improvisación.

## 18. Decisiones abiertas

- [x] Markdown + YAML confirmado mediante ADR-0004.
- [x] `.trufagent/` confirmado frente a `docs/context/` mediante ADR-0004.
- [ ] Definir schema formal JSON Schema.
- [ ] Elegir ULID u otro identificador.
- [ ] Definir límites de tamaño y cantidad del paquete.
- [ ] Elegir estrategia de búsqueda inicial: texto, SQLite FTS o híbrida.
- [x] Integrar Graphify-Labs/graphify como cartografía obligatoria.
- [x] `team` es versionable; `project` y `user` son locales por defecto.

## 19. Handoff

Estado: listo para revisión de producto y arquitectura, no para implementación
directa.

Después de resolver las decisiones abiertas, crear:

1. JSON Schema de `trufagent.memory.v1`;
2. fixtures derivados de C02, C05, C09 y C10;
3. prototipo local de `search/read/propose/validate`;
4. pruebas de recuperación y contaminación.
