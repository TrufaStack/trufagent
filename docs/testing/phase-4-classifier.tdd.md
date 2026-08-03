# Fase 4 — Evidencia TDD del clasificador de tareas

Fecha: 2026-07-30

## Alcance

- señales de tarea tipadas;
- clasificación determinista y explicable;
- presupuestos independientes de exploración, ejecución y verificación;
- niveles extremos `none` y `critical`;
- escaladores de secretos, producción, persistencia, permisos, contratos,
  superficies, estado, visuales y artefactos;
- frontera de autonomía y evidencia requerida;
- entrada CLI desde JSON.

## RED

La prueba inicial no pudo importar
`trufagent.application.task_classifier`. La matriz C01–C12 se escribió antes
de implementar el clasificador.

## GREEN

Los 12 casos reales reproducen la matriz del casebook:

- C01 permanece pequeño;
- C02/C07 exigen descubrimiento sistemático;
- C05 mantiene ejecución baja y verificación crítica;
- C09 permite ejecución nula;
- C10 bloquea improvisación sin el Artifact aprobado;
- C12 aprovecha el plan resuelto con exploración baja.

Se añadieron controles para determinismo, razones auditables y riesgo crítico
sin inflación de ejecución.

Resultado final de la suite:

```text
45 passed
```

Cobertura focalizada:

```text
98% sobre 203 statements
```

## Uso

```text
trufagent plan classify signals.json
```

El archivo se valida con `TaskSignals`; campos desconocidos fallan por diseño.
Esta fase no infiere señales desde lenguaje natural, evitando esconder
decisiones de clasificación dentro de prompts no auditables.
