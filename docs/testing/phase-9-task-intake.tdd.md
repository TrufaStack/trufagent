# Fase 9 — Evidencia TDD de Task Intake

Fecha: 2026-07-30

## RED

Las pruebas iniciales fallaron porque `application.task_extractor` no existía.
Se fijaron primero cambios pequeños, bugs silenciosos, síntomas compartidos,
Artifacts ausentes, correcciones, determinismo y CLI.

## Evaluación Casebook

Después del primer GREEN se añadieron C03, C04, C05, C06, C08, C09, C11 y C12
para cubrir roles, arquitectura, diagnósticos, librerías, visual, investigación
y planes aprobados.

La evaluación corrigió dos falsos positivos:

- `solo lectura` de UI no se trata como restricción externa;
- comandos de diagnóstico no se clasifican como bug de producto.

El smoke real corrigió un tercero: “answers disappear after navigation”
describía una secuencia de reproducción y no debía activar evidencia visual.
La regla quedó limitada a navegación explícitamente mobile/bottom-nav.

## Composición

`PrepareTaskService` entrega señales a `PlanTaskService` únicamente cuando
`ready_to_plan=true`. Un Artifact faltante devuelve preguntas y `plan=null`.

Resultado focalizado:

```text
17 passed
98% coverage
```

La baseline no consume tokens de modelos ni requiere API keys.
