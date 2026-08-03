# Trufagent v2 — Transition Map

## Propósito

Este documento traduce el `PRODUCT-BRIEF` de v2 al código existente de v1.
Clasifica cada subsistema y establece un orden de migración que mantenga
operativo el ciclo esencial.

Las acciones posibles son:

- **conservar**: la capacidad ya corresponde al MVP;
- **simplificar**: conservar la intención con un contrato menor;
- **experimental**: retirar de la ruta principal sin borrar todavía;
- **retirar**: eliminar después de desacoplar sus consumidores.

## Objetivo estructural

El runtime v2 debe tener un único recorrido principal:

```text
intake
  → complejidad + skills + modelo
  → memoria + Graphify
  → handoff al anfitrión
  → implementación y verificación en el anfitrión
  → confirmación del merge
  → resumen + propuestas de memoria + refresh del grafo
```

Codex y Claude Code siguen siendo anfitriones. Trufagent prepara contexto y
comportamiento; no ejecuta un segundo sistema de coordinación.

## Mapa de capacidades

| Capacidad v1 | Acción | Resultado esperado en v2 |
| --- | --- | --- |
| Memoria Markdown | Simplificar | Entradas breves, búsqueda económica y actualización explícita |
| Índice SQLite de memoria | Conservar | Índice derivado y regenerable para acceso rápido |
| Revisión de memoria | Simplificar | Proponer, aceptar, reemplazar y retirar sin una máquina de estados extensa |
| Graphify | Conservar | Estado, consulta, impacto y actualización posterior al merge |
| Intake de tarea | Simplificar | Pocas clases y señales explicables |
| Clasificador | Simplificar | Complejidad, esfuerzo, skills y tier de modelo en una sola decisión compacta |
| Context builder | Simplificar | Un paquete acotado con memoria y referencias estructurales |
| Enrutamiento de modelos | Conservar | `economy`, `balanced` y `frontier`, resueltos por anfitrión |
| Catálogo de skills | Simplificar | Metadatos compactos, selección mínima y carga diferida |
| Adaptadores Codex/Claude | Conservar | Skills delgadas sobre el mismo runtime |
| Sesiones y handoff | Simplificar | Preparación y cierre compacto alrededor del merge |
| Project init | Conservar | Configuración mínima del proyecto |
| Task previews y continuation | Experimental | Fuera del flujo principal hasta demostrar necesidad |
| Graphify-first gates | Simplificar | Una decisión local: consultar, abstenerse o refrescar |
| Coordinator gate | Retirar | El anfitrión siempre coordina; no requiere un gate runtime |
| Delegation protocol | Experimental | No se carga ni condiciona el MVP |
| Shadow execution | Experimental | Aislado de CLI, planificación y dependencias principales |
| Retry gate | Experimental | Conservado únicamente junto a shadow |
| Attempt y usage ledgers | Experimental | Sin escritura en el flujo normal |
| Context projection para shadow | Experimental | Mantener solo dentro del paquete experimental |
| Promoción y pilotos | Retirar | No forman parte del producto v2 |
| Codex managed skill surface | Retirar | Trufagent no administra globalmente todas las skills de Codex |
| Evaluaciones deterministas del core | Conservar | Casos pequeños del ciclo esencial |
| Canaries y live evals de proveedores | Experimental | Suite separada, nunca requisito del runtime |

## Mapa del código

### Conservar

Estos módulos contienen capacidades directamente necesarias, aunque pueden
recibir ajustes durante la migración:

- `application/context_builder.py`;
- `application/model_routing.py`;
- `application/skill_catalog.py`;
- `domain/cartography.py`;
- `domain/context.py`;
- `domain/skills.py`;
- `infrastructure/graphify_adapter.py`;
- `infrastructure/memory_index.py`;
- `infrastructure/model_profiles.py`;
- `infrastructure/project_init.py`;
- `infrastructure/skill_catalog_fs.py`;
- `infrastructure/skill_discovery.py`;
- `infrastructure/worktree_fingerprint.py`.

También se conservan como superficies:

- `adapters/codex/skills/`;
- `skills/trufagent/`;
- `skills/start-session/`;
- `skills/end-session/`.

### Simplificar

#### Intake, estrategia y plan

- `domain/task.py` tiene demasiadas dimensiones y señales.
- `application/task_extractor.py` infiere una matriz extensa de booleanos.
- `application/task_classifier.py` mezcla clasificación, riesgo, autonomía,
  evidencia y selección parcial de skills.
- `application/plan_task.py` compone gates y contratos que pueden reducirse.
- `application/prepare_task.py` debe convertirse en la entrada principal del
  runtime.

El resultado v2 debe contener solamente:

- tipo de tarea;
- complejidad;
- tier de modelo;
- esfuerzo por fase;
- skills seleccionadas y motivo;
- referencias de memoria y grafo;
- advertencias accionables.

#### Memoria

- `domain/memory.py` conserva más metadatos de los necesarios para una memoria
  personal ágil.
- `infrastructure/memory_markdown.py` y `memory_fs.py` deben mantener Markdown
  como autoridad, con índices derivados.
- `application/memory_review.py` debe reducir la revisión a operaciones humanas
  explícitas y comprensibles.

La transición debe preservar las memorias existentes mediante lectura
compatible o una migración reversible.

#### Sesiones y cierre

- `application/sessions.py`;
- `domain/session.py`;
- `infrastructure/session_fs.py`.

Se conserva un handoff compacto, pero el cierre v2 ocurre después de confirmar
el merge. El resultado propone cambios de memoria y decide si Graphify debe
actualizarse. No necesita conservar una bitácora completa de cada sesión.

#### CLI

`src/trufagent/cli.py` concentra 1,416 líneas y todas las capacidades del
producto. Debe dividirse por comandos y reducir su superficie pública.

La superficie objetivo es:

```text
trufagent prepare
trufagent memory search|show|propose|accept|retire
trufagent graph status|query|affected|update
trufagent models resolve
trufagent skills list|select
trufagent close
trufagent init
```

Durante la transición pueden mantenerse aliases de compatibilidad para
`plan prepare`, `cartography` y `session end`.

### Experimental

Estos módulos deben moverse detrás de una frontera explícita y dejar de ser
importados por el CLI y el plan principal:

- `application/delegation.py`;
- `application/delegation_executor.py`;
- `application/retry_gate.py`;
- `domain/attempt.py`;
- `domain/delegation.py`;
- `infrastructure/attempt_fs.py`;
- `infrastructure/codex_shadow_runner.py`;
- `infrastructure/context_projection.py`;
- `infrastructure/fake_phase_adapter.py`;
- `infrastructure/shadow_phase_adapter.py`;
- `infrastructure/task_preview_fs.py`;
- `infrastructure/usage_fs.py`;
- `domain/task_preview.py`.

Destino provisional:

```text
src/trufagent/experimental/
```

La migración física debe ocurrir solo después de cortar imports desde el core.
Las pruebas correspondientes se separan como suite experimental y no bloquean
la evolución del MVP salvo que ese paquete sea modificado.

### Retirar

Después de verificar que no tienen consumidores en el core:

- `application/coordinator_gate.py`;
- `application/promotion.py`;
- `infrastructure/pilot_fs.py`;
- `infrastructure/promotion_fs.py`;
- `infrastructure/promotion_review.py`;
- `infrastructure/promotion_workspace.py`;
- `infrastructure/codex_skill_surface.py`.

También se retiran del CLI:

- `promotion *`;
- `delegation *` de la superficie estable;
- `skills profile` como administrador global de Codex;
- ledgers de attempts y usage.

No se elimina código en el mismo cambio que redefine contratos del core. Cada
retiro debe tener una búsqueda de consumidores y una prueba de regresión del
vertical slice.

## Mapa de pruebas

### Suite esencial v2

Debe validar como mínimo:

1. intake pequeño → `economy`, contexto mínimo y ninguna skill innecesaria;
2. bug incierto → skill de debugging y esfuerzo de exploración mayor;
3. feature normal → `balanced`, memoria y Graphify acotados;
4. arquitectura ambigua → `frontier` y skills complementarias justificadas;
5. selección forzada o excluida por el usuario;
6. memoria recuperada dentro de presupuesto y con procedencia;
7. Graphify fresco, obsoleto y no aplicable;
8. cierre rechazado antes del merge confirmado;
9. cierre posterior al merge → resumen, propuestas y refresh requerido;
10. equivalencia básica entre adaptadores Codex y Claude.

### Suite experimental

Se mueven fuera del gate principal las pruebas de:

- shadow y canaries;
- protocolos y ejecución de delegación;
- reintentos de proveedor;
- attempts y usage;
- promoción, workspaces y pilotos;
- managed skill surface de Codex;
- live evals dependientes de proveedores.

Las pruebas no se borran al aislar una capacidad. Primero dejan de condicionar
el MVP; después se decide si el experimento merece mantenimiento.

## Documentación

- `docs/v2/PRODUCT-BRIEF.md` es la fuente de verdad del producto.
- Este documento gobierna la transición técnica.
- `docs/v1/` permanece como referencia histórica, no como contrato vigente.
- `docs/testing/` conserva evidencia histórica hasta completar la migración.
- Los documentos de delegación, shadow y promoción deben marcarse como
  experimentales o archivarse cuando el código cambie de ubicación.

## Fases de migración

### Fase 0 — Baseline

Estado actual:

- v1 preservado en Git;
- suite existente verde;
- Graphify disponible;
- brief v2 definido.

### Fase 1 — Contrato v2 ejecutable

Crear modelos pequeños para `prepare` y `close`, acompañados por diez casos de
aceptación del ciclo esencial. Todavía pueden adaptarse internamente sobre los
servicios v1.

Resultado: el comportamiento deseado existe antes de podar infraestructura.

### Fase 2 — Preparación compacta

Reducir intake, clasificación, selección de skills, routing y contexto a un
único servicio v2. Mantener aliases CLI de compatibilidad.

Resultado: fixes y features usan el nuevo vertical slice.

### Fase 3 — Memoria ágil y cierre post-merge

Simplificar el esquema de memoria y crear el cierre condicionado al merge.
Mantener lectura compatible de memoria v1 y reconstrucción del índice.

Resultado: el ciclo completo puede aprender sin acumular historial innecesario.

### Fase 4 — Aislar experimentos

Cortar imports del core hacia shadow, delegación, previews y ledgers. Mover el
código y sus pruebas bajo una frontera experimental.

Resultado: el runtime estable no carga ni conoce esos subsistemas.

### Fase 5 — Retirar complejidad

Eliminar promoción, pilotos, coordinator gate y administración global de skills.
Dividir el CLI y archivar documentación v1 que ya no describe el producto.

Resultado: la estructura física refleja el brief v2.

## Reglas de transición

- Mantener una ruta funcional para `prepare` durante toda la migración.
- No cambiar esquema de memoria y poda de subsistemas en el mismo commit.
- No eliminar una capacidad hasta cortar y verificar todos sus consumidores.
- Actualizar Graphify después de cada cambio estructural confirmado.
- Comparar el coste de contexto del vertical slice antes y después.
- Preferir compatibilidad temporal a adaptadores duplicados.
- Cada fase termina con tests, lint y un resumen de impacto.

## Primera tarea de implementación

Definir el contrato de salida de `trufagent prepare` v2 y escribir sus casos de
aceptación sin modificar todavía el comportamiento de v1. Este contrato será el
punto de unión para memoria, Graphify, skills, routing y adaptadores.
