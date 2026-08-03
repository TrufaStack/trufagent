# Fase 5 — Evidencia TDD de `plan_task`

Fecha: 2026-07-30

## Alcance

La primera línea vertical compone:

```text
memoria dirigida
+ cartografía Graphify
+ clasificación de esfuerzo
+ catálogo revisado de skills
→ TaskPlan
```

## Contrato

`PlanTaskRequest` contiene:

- tarea y proyecto;
- raíz normalizada;
- `TaskSignals` explícitas;
- presupuestos de memoria y cartografía;
- opt-in de memoria personal;
- skills forzadas y excluidas.

`TaskPlan` devuelve:

- estrategia y presupuestos;
- referencias de memoria por autoridad;
- nodos estructurales;
- skills seleccionadas con procedencia y versión;
- evidencia requerida;
- warnings y frontera de autonomía;
- resumen compacto.

## RED

Las pruebas iniciales fallaron al importar `application.errors`,
`application.plan_task` y `application.skill_catalog`, escritos después del
contrato.

## GREEN

Se verificó que:

- C02 recupera el riesgo, el símbolo estructural y `systematic-debugging`;
- una caída de Graphify degrada una tarea trivial;
- la misma caída bloquea arquitectura/impacto;
- una skill ausente o no revisada no se activa;
- una exclusión explícita gana;
- un Artifact aprobado ausente sigue bloqueando después de componer;
- el CLI construye un plan completo desde JSON.

Resultado:

```text
50 passed
```

Cobertura focalizada:

```text
96% total
100% plan_task
100% skill_catalog
```

## CLI

Clasificación aislada:

```text
trufagent plan classify signals.json
```

Plan completo después de `trufagent init`:

```text
trufagent plan task request.json
```

`--catalog` permite sobrescribir la ruta YAML configurada para un uso puntual.
Sin configuración ni override, el catálogo activo queda vacío; nunca se asume
que toda skill instalada está revisada.
