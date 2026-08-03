# Trufagent v1 — Correctable Task Intake

Fecha: 2026-07-30

## Propósito

Convertir una solicitud natural en `TaskSignals` sin ocultar inferencias. La
salida incluye evidencia, confianza, preguntas y estrategia provisional.

La primera versión es determinista, local y bilingüe. No llama modelos ni APIs.
Su objetivo es producir una baseline medible antes de añadir una capa
probabilística.

## Entrada

```json
{
  "task": "Diagnose why checklist answers disappear.",
  "signal_overrides": {
    "kind": "bug"
  }
}
```

Los overrides se validan contra `TaskSignals`, reemplazan cualquier inferencia
del mismo campo y se registran como `source: user`, confianza 1.0 y corrección
explícita.

## Salida

```text
signals
evidence[]
questions[]
ready_to_plan
strategy
```

Una señal no detectada conserva su default seguro y no se presenta como
evidencia.

## Reglas importantes

- El mismo síntoma en dos superficies activa `shared_symptom`, no
  `shared_contract`.
- Visibilidad para admins no implica por sí sola cambios de autorización.
- Read-only de UI no implica una restricción externa.
- Un Artifact aprobado sin referencia accesible bloquea planificación.
- Diagnóstico de entorno se separa de un bug de producto.
- Correcciones explícitas siempre ganan.

## Flujo

```text
TaskIntake
→ extract_task_signals
→ preguntas bloqueantes?
   ├─ sí: devolver extracción sin plan
   └─ no: PlanTaskService
```

## CLI

```text
trufagent plan extract intake.json
trufagent plan prepare intake.json <project-root> --project <id>
```

`prepare` carga automáticamente memoria, Graphify y catálogo de skills.

Para uso cotidiano, la fachada compacta evita construir el JSON manualmente:

```text
trufagent task "Agregar un badge temporal con fechas fijas" \
  --root . \
  --project my-project
```

El comando abre o reutiliza una sesión, extrae señales, prepara el plan y
devuelve un preview compacto con ruta, skills, IDs de memoria, objetivos
estructurales, advertencias y siguiente acción. No invoca proveedores ni
modifica código.

Las correcciones siguen siendo explícitas y auditables:

```text
trufagent task "Update the map control" \
  --kind bug \
  --cause-known \
  --localized \
  --required-symbol AttributionControl
```

El texto libre no se persiste como objetivo de sesión. Trufagent almacena
solamente un digest corto; esto evita convertir historiales de sesión en una
fuente accidental de secretos.

## Continuación guiada

Un preview listo incluye un `preview_id` y dos rutas explícitas:

```text
trufagent task-continue <preview-id> --mode local
trufagent task-continue <preview-id> --mode shadow --task-text "<request>"
```

La primera llamada solicita confirmación y no ejecuta nada. Con `--confirm`, el
modo local devuelve un handoff acotado por skills, memoria, targets y evidencia.
El modo shadow verifica que el texto coincida con el digest y prepara los
requisitos de presupuesto; no invoca un proveedor automáticamente.

Los previews persistidos contienen decisiones seguras y digests, nunca el texto
natural de la tarea.

## Límites

Las heurísticas no deben presentarse como comprensión del dominio. Una fase
posterior podrá añadir un extractor LLM detrás del mismo contrato, conservando
evidencia y correcciones, solamente si las mediciones justifican su costo.
