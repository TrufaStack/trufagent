# Fase 6 — Catálogo personal e inicialización

Fecha: 2026-07-30

## Catálogo

Ruta personal:

```text
~/.trufagent/skills/catalog.yaml
```

El discovery inspecciona:

- `~/.claude/skills`;
- `~/.codex/skills`;
- roots de plugins activos declarados en `installed_plugins.json`.

No recorre snapshots antiguos de plugins. Cada entrada conserva fingerprint,
descripción, origen, versión y ubicaciones.

## Reglas de confianza

- instalada no significa revisada;
- copias idénticas se deduplican y combinan ubicaciones;
- variantes con el mismo nombre y diferente fingerprint quedan inactivas;
- revisar una variante conflictiva puede activarla y desactivar las otras;
- la variante activa revisada sobrevive a sincronizaciones posteriores;
- un cambio de fingerprint revoca la revisión durante el siguiente sync;
- frontmatter inválido cae a metadata mínima, nunca gana confianza.

## Estado personal inicial

El primer sync encontró 384 variantes y cuatro entradas inactivas pertenecientes
a dos conflictos de nombre.

Se revisaron explícitamente cinco skills respaldadas por el historial del
usuario:

- `brainstorming` 6.2.0;
- `writing-plans` 6.2.0;
- `systematic-debugging` 6.2.0;
- `graphify` 0.9.30;
- la variante actual de `ui-ux-pro-max`.

Las demás permanecen sin revisar.

La verificación final detectó y corrigió una regresión donde la variante
`ui-ux-pro-max` conservaba `reviewed: true` pero perdía su selección activa tras
sincronizar. La elección por fingerprint ahora persiste y tiene prueba de
regresión.

## Inicialización

```text
trufagent init <project-root> --project <id>
```

Crea el vault protegido y `.trufagent/config.yaml`. La operación es idempotente
para una configuración idéntica y falla si intentara sobrescribir otra.

El propio repositorio Trufagent quedó inicializado con el catálogo personal.

## Smoke

Un `plan task` ejecutado sin `--catalog` cargó automáticamente la configuración
del proyecto y seleccionó:

```text
systematic-debugging
source: claude-plugin:superpowers@claude-plugins-official
```

Como el proyecto todavía no tiene grafo, una tarea de persistencia terminó
correctamente en `autonomy=block` con evidencia `refresh-cartography`.
