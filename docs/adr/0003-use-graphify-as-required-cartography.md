# ADR-0003: Usar Graphify como cartografía obligatoria

**Fecha**: 2026-07-30  
**Estado**: accepted  
**Decisores**: autor de Trufagent y Codex

## Contexto

Trufagent necesita evitar que cada agente reconstruya la arquitectura del
repositorio mediante lecturas y búsquedas repetidas. Graphify-Labs/graphify
genera localmente un grafo de código, documentación, esquemas y relaciones que
puede consultarse por CLI o MCP. Sin embargo, sus datos son derivados y no
incluyen por sí solos el gobierno, la autoridad ni el ciclo de vida de la
memoria de Trufagent.

## Decisión

Trufagent integra obligatoriamente
[Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify), distribuido
como paquete `graphifyy` y ejecutado mediante `graphify`, como motor de
cartografía estructural.

Graphify identifica entidades, relaciones, comunidades y caminos del
repositorio. Trufagent conserva por separado la memoria gobernada: reglas,
decisiones, riesgos, incidentes, lecciones, artefactos, preferencias y estado.

Los documentos canónicos pueden ser indexados y enlazados desde Graphify, pero
el grafo no reemplaza su contenido, autoridad ni ciclo de aprobación. El código,
los tests, las specs y los documentos aprobados continúan siendo las fuentes
canónicas correspondientes.

## Alternativas consideradas

### Cartografía intercambiable con varios proveedores

- **Ventajas**: menor acoplamiento y posibilidad de comparar motores.
- **Desventajas**: obliga a diseñar para capacidades mínimas antes de validar la
  experiencia principal.
- **Por qué no**: el usuario requiere Graphify y su integración concreta permite
  probar la tesis con una herramienta real.

### Usar Graphify como memoria completa

- **Ventajas**: un único índice y una superficie de consulta.
- **Desventajas**: mezcla hechos derivados con decisiones humanas, no ofrece por
  sí solo aprobación, supersesión, scopes ni políticas de seguridad.
- **Por qué no**: un grafo estructural no debe determinar qué reglas gobiernan
  el comportamiento.

### Mantener solo Markdown y búsquedas de texto

- **Ventajas**: implementación simple y completamente legible.
- **Desventajas**: obliga a reconstruir dependencias y radio de impacto en cada
  sesión.
- **Por qué no**: contradice el objetivo de reducir lecturas repetidas en
  repositorios grandes.

## Consecuencias

### Positivas

- Trufagent dispone de una cartografía local y consultable desde el inicio.
- Las memorias pueden relacionarse con símbolos y módulos reales.
- Las búsquedas de radio de impacto comienzan con estructura en vez de texto.
- Claude Code y Codex pueden compartir el mismo grafo.

### Negativas

- Graphify se convierte en dependencia del flujo completo de Trufagent.
- Cambios en su CLI, MCP o formato de salida requerirán adaptación.
- La instalación y el diagnóstico deben gestionar una herramienta adicional.
- Se necesita una política explícita de frescura y regeneración.

### Riesgos

- **Grafo obsoleto**: registrar commit de origen y bloquear usos estructurales de
  alto riesgo hasta regenerar.
- **Confundir índice con verdad**: verificar código y documentos canónicos antes
  de modificar.
- **Acoplamiento directo**: encapsular CLI, MCP y formatos detrás de un módulo
  interno de cartografía, aunque no se prometa otro proveedor en v1.
- **Fallo de Graphify**: permitir degradación visible solo para tareas triviales
  y localizadas.

## Contrato de degradación

- Una tarea trivial y localizada puede continuar sin grafo, anunciando la
  degradación.
- Refactors, arquitectura y análisis de impacto requieren un grafo vigente.
- Un grafo basado en otro commit no sirve como evidencia actual sin
  revalidación.
- Las reglas críticas de seguridad se aplican incluso si Graphify no está
  disponible.

## Referencias

- [Product Brief](../v1/PRODUCT-BRIEF.md)
- [Behavior Contract, Cartografía](../v1/BEHAVIOR-CONTRACT.md#4-cartografía)
- [Memory Schema, Graphify](../v1/MEMORY-SCHEMA.md#12-cartografía-y-graphify)
- [Documentación oficial de Graphify](https://graphify.com/docs)
