# Fase 7 — Evidencia TDD de sesiones

Fecha: 2026-07-30

## RED

Ocho contratos se escribieron antes de los módulos de sesión:

- start idempotente;
- journal y handoff sin Git;
- recuperación compacta;
- propuestas no gobernantes;
- bloqueo de secretos;
- validación de session ID;
- prohibición de memoria personal implícita;
- ciclo CLI completo.

La primera ejecución falló al importar `application.sessions`.

## Hallazgo de seguridad

El caso de contraseña descubrió que el patrón existente de asignaciones
excluía accidentalmente la letra `s` en lugar de whitespace. Una contraseña que
comenzaba con esa letra podía escapar. La expresión fue corregida y el caso
permanece como regresión.

## GREEN

El cierre:

- valida todas las propuestas antes de archivar;
- conserva la sesión activa ante contenido inseguro;
- escribe journals create-only;
- genera handoff atómico;
- nunca acepta memorias gobernantes ni ejecuta commits.

La suite focalizada terminó con ocho pruebas aprobadas.
