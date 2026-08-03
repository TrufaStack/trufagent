# Trufagent v2 — Skill Library

## Objetivo

La biblioteca de skills permite descubrir conocimiento procedimental instalado
sin cargar todas sus instrucciones en el contexto. Trufagent consulta
metadatos, recomienda el conjunto mínimo y abre un `SKILL.md` solamente cuando
la tarea y el anfitrión lo requieren.

## Fuentes locales

El inventario se reconstruye desde:

- `~/.codex/skills`;
- `~/.claude/skills`;
- las roots de skills declaradas por plugins instalados de Claude.

Cada variante conserva nombre, descripción, fuente, versión, fingerprint,
estado de revisión y todas sus ubicaciones. Dos implementaciones con el mismo
nombre pueden coexistir cuando pertenecen a anfitriones diferentes. Solo se
consideran conflicto cuando compiten dentro del mismo anfitrión.

## Descubrimiento y confianza

```bash
trufagent skills sync
```

La sincronización:

- añade y actualiza el inventario local;
- conserva una revisión únicamente si el fingerprint no cambió;
- no activa ni aprueba contenido nuevo;
- detecta variantes conflictivas;
- no descarga skills ni ejecuta sus instrucciones.

La biblioteca completa puede explorarse con:

```bash
trufagent skills search "systematic debugging" --harness codex
trufagent skills search "database migration" --include-unreviewed
```

## Evaluación local

El inventario completo se evalúa sin conceder confianza:

```bash
trufagent skills audit
```

La auditoría genera `~/.trufagent/skills/audit.json` y clasifica cada fingerprint
como `candidate`, `review` o `blocked`. Comprueba disponibilidad, calidad mínima
de descripción, tamaño del paquete, scripts y señales estáticas como comandos
destructivos, rutas de credenciales, configuración sensible, descarga seguida de shell, red, `sudo` e
intentos explícitos de sustituir instrucciones. Es un filtro conservador: un
resultado limpio sigue necesitando revisión humana antes de cambiar `reviewed`.

## Fuentes remotas gobernadas

El piloto consulta únicamente metadatos públicos de cuatro repositorios:

- `anthropics/skills`;
- `addyosmani/agent-skills`;
- `huggingface/skills`;
- `MicrosoftDocs/Agent-Skills`.

```bash
trufagent skills sources
```

El resultado se guarda en `~/.trufagent/skills/sources.json` con procedencia,
nivel de confianza, propósito, estrellas, forks, licencia, actividad, rama y el
commit exacto observado. Este comando no clona, instala ni ejecuta contenido.
También inventaría los `SKILL.md` y scripts del commit, calcula fingerprints,
señala coincidencias locales y aplica el filtro estático al texto remoto en
memoria. No conserva los cuerpos descargados.
Una futura importación deberá fijarse a ese commit y pasar por la misma auditoría
local antes de ser candidata a revisión.

Las decisiones del primer piloto, incluidos solapamientos y adaptaciones, están
registradas en [`SKILL-SOURCE-REVIEW.md`](SKILL-SOURCE-REVIEW.md).

## Sanitización conservadora

La biblioteca heredada puede clasificarse sin mover archivos:

```bash
trufagent skills sanitize --plan
```

El manifiesto `~/.trufagent/skills/sanitization-plan.json` asigna a cada
fingerprint un nivel (`core`, `profile`, `cold` o `quarantine`), una capacidad,
un canon sugerido entre variantes del mismo nombre y anfitrión, razones y una acción
propuesta. El plan siempre informa `mutations: 0`; todavía no existe un modo
`--apply`. Las entradas de cuarentena apuntan a un archivo recuperable bajo
`~/.trufagent/skills/archive/v1`, pero no se trasladan hasta que el manifiesto
sea revisado y aprobado. Una aplicación aprobada usa
`trufagent skills sanitize --apply <manifest>`: mueve únicamente skills de
raíces personales al archivo recuperable y marca las variantes administradas
por plugins como `quarantined`, sin alterar sus cachés.

La selección automática solo utiliza entradas activas, disponibles y
revisadas. `--include-unreviewed` sirve para descubrimiento humano, no concede
confianza ni autorización de ejecución.

## Selección por anfitrión

Cuando una skill tiene varias ubicaciones, Trufagent prefiere la variante del
anfitrión solicitado:

- `--harness codex` prioriza ubicaciones Codex;
- `--harness claude` prioriza ubicaciones Claude y plugins Claude.

Si no existe una variante nativa, la biblioteca puede devolver una ubicación
Markdown revisada de otro anfitrión como fallback visible. El resultado siempre
incluye `platform` y `location`; el adaptador decide si puede consumirla.

## Recomendación

El clasificador produce necesidades procedimentales pequeñas, por ejemplo:

- causa de un fix no demostrada → `systematic-debugging`;
- decisiones abiertas → `brainstorming`.

La biblioteca resuelve esas necesidades contra el inventario activo. Con el
tiempo pueden añadirse capacidades como planificación, TDD, diseño visual o
migraciones, pero deben seleccionarse por evidencia de la tarea y no por el
tamaño de la biblioteca.

## Límites

- Inventariar una skill no significa confiar en ella.
- Una puntuación de auditoría no equivale a aprobación funcional ni de seguridad.
- Revisar una variante no revisa automáticamente otra con el mismo nombre.
- Una búsqueda usa nombre y descripción; no carga el cuerpo completo.
- Trufagent no administra globalmente qué skills muestra Codex o Claude.
- La biblioteca no reemplaza las reglas nativas de activación del anfitrión.
