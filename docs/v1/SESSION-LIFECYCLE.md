# Trufagent v1 — Session Lifecycle

Fecha: 2026-07-30

## Propósito

Una sesión conserva únicamente continuidad operativa: objetivo actual, resumen
del cierre y siguiente acción concreta. No intenta reconstruir la conversación
ni convierte automáticamente hallazgos en verdad durable.

## Legacy revisado

Las antiguas `start-session` y `end-session` aportaban:

- lectura explícita al comenzar;
- journal cronológico;
- siguiente paso concreto;
- cierre antes de agotar contexto.

Sus límites eran:

- rutas fijas bajo `docs/context/`;
- `state.md` monolítico y manual;
- dependencia de detalles de Claude Code;
- commit automático de journals;
- lecciones sin ciclo formal de revisión.

## Diseño v1

```text
.trufagent/state/
├── current-session.yaml
├── handoff.yaml
└── sessions/
    └── ses_<timestamp>_<suffix>.md
```

Todo el directorio `state/` es efímero e ignorado por Git.

### Start

- devuelve la sesión activa si ya existe;
- recupera únicamente el último handoff compacto;
- nunca barre todos los journals;
- no inicia trabajo ni herramientas.

### End

- exige el ID de la sesión activa;
- escribe un journal create-only;
- reemplaza atómicamente el handoff;
- elimina el marcador de sesión activa;
- no ejecuta Git;
- puede crear propuestas de memoria.

## Promoción a memoria

Toda propuesta creada al cerrar:

```text
status: proposed
trust: unreviewed
created_by: trufagent-session
```

No gobierna comportamiento. Los scopes permitidos son `project` y `team`;
`user` requiere una acción explícita separada.

El lote se inspecciona por formas de secretos antes de cerrar. Si falla, la
sesión permanece activa.

## CLI

```text
trufagent session start <root> --project <id> --objective "<objetivo>"
trufagent session status <root>
trufagent session end <root> end-session.json --project <id>
```

El request de cierre es JSON tipado y visible. Se omiten secciones vacías del
journal.
