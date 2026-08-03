# Fase 8 — Evidencia TDD de revisión humana

Fecha: 2026-07-30

## Contrato

- aceptar no reescribe el Markdown;
- solo `accepted` revisado puede gobernar;
- rechazo exige razón y sale del recall ordinario;
- supersede exige reemplazo aceptado y enlaza su ID;
- transiciones inválidas fallan;
- todo evento conserva reviewer y timestamp;
- el índice FTS5 se reconstruye después de revisar;
- CLI permite listar, mostrar, revisar e inspeccionar historial.

## RED

Las pruebas se escribieron antes de `application.memory_review` y fallaron
durante importación.

## GREEN

Siete pruebas focalizadas cubren:

- `proposed → accepted`;
- `proposed → rejected`;
- `accepted → superseded`;
- preservación byte a byte del Markdown;
- exclusión de estados inactivos;
- actualización del índice;
- flujo CLI e historial.

Cobertura focalizada: 91% sobre 303 statements.

## CLI

```text
trufagent memory list <root> --project <id> --status proposed
trufagent memory show <root> <memory-id> --project <id>
trufagent memory history <root> <memory-id> --project <id>
trufagent memory accept <root> <memory-id> --project <id> --reviewer <name>
trufagent memory reject <root> <memory-id> --project <id> \
  --reviewer <name> --reason "<razón>"
trufagent memory supersede <root> <memory-id> --with <replacement-id> \
  --project <id> --reviewer <name> --reason "<razón>"
```

Las operaciones son locales y no ejecutan Git.
