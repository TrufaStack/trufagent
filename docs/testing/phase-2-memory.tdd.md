# Fase 2 — Evidencia TDD de memoria y context packets

Fecha: 2026-07-30

## Alcance

- vault Markdown/YAML con scopes `project`, `team` y `user`;
- protección `.gitignore` fail-closed;
- escritura create-only y aislamiento por proyecto;
- recuperación normal sin estados rechazados, obsoletos o reemplazados;
- índice derivado SQLite FTS5;
- context packets con ranking, presupuesto y autoridad explícita.

## RED

Comando:

```text
uv run pytest tests/test_memory_repository.py tests/test_memory_index.py tests/test_context_builder.py
```

Resultado inicial: tres errores de colección porque `memory_fs`,
`memory_index` y `context_builder` todavía no existían.

## GREEN

El primer ciclo de implementación produjo 7 pruebas aprobadas y 4 fallos de
contrato en fixtures. Se ajustaron las pruebas para respetar los scopes reales:
C02 es memoria de equipo, C05 es memoria personal y por tanto requiere opt-in.

Resultado final:

```text
11 passed
```

Suite completa:

```text
22 passed
```

## Cobertura focalizada

Comando:

```text
uv run pytest tests/test_memory_repository.py tests/test_memory_index.py \
  tests/test_context_builder.py \
  --cov=trufagent.infrastructure.memory_fs \
  --cov=trufagent.infrastructure.memory_index \
  --cov=trufagent.application.context_builder \
  --cov=trufagent.domain.context
```

Resultado: 97% sobre los módulos nuevos de la fase (169 statements, 5 sin
cubrir).

La cobertura del paquete completo es 70% porque el scaffold ya contiene puertos
y modelos de fases futuras todavía sin ejecución. No se maquilló ese valor
excluyéndolos de la configuración global.

## Controles verificados

- La modificación manual de la política de protección detiene la inicialización.
- La memoria personal no se recupera implícitamente.
- Un ID no puede crearse dos veces ni cruzar proyectos.
- SQLite puede borrarse y reconstruirse sin pérdida canónica.
- Memoria propuesta/no revisada aparece con advertencia y no gobierna.
- El paquete no excede su presupuesto y declara cuántos candidatos omitió.
