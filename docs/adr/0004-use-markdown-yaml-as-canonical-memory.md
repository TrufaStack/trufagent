# ADR-0004: Usar Markdown con YAML como memoria canónica

**Fecha**: 2026-07-30  
**Estado**: accepted  
**Decisores**: autor de Trufagent y Codex

## Contexto

Trufagent necesita conservar reglas, decisiones, riesgos, incidentes, lecciones
y referencias de forma durable y portable. La memoria debe poder revisarse por
personas, compararse en Git y compartirse entre Claude Code y Codex. Graphify
puede indexarla y conectarla con código, pero sus artefactos son derivados y no
ofrecen el ciclo de aprobación requerido.

## Decisión

Trufagent usa documentos Markdown con frontmatter YAML como memoria canónica.
Los índices de búsqueda, bases de datos y grafos son derivados y regenerables.

La estructura inicial es:

```text
.trufagent/
├── memory/
│   ├── project/    # local, ignorada por Git
│   └── team/       # revisada y versionable
├── state/          # estado temporal
└── cartography/    # metadatos del adaptador de Graphify

~/.trufagent/
└── memory/
    └── user/       # reglas y preferencias personales
```

Las propuestas creadas por agentes comienzan como `unreviewed`. Las reglas y
decisiones no gobiernan comportamiento hasta ser aceptadas. Graphify puede
indexar y enlazar estos documentos, pero no controla su autoridad, estado,
promoción ni supersesión.

## Alternativas consideradas

### SQLite como fuente canónica

- **Ventajas**: consultas, filtros e índices eficientes.
- **Desventajas**: revisión manual y diffs deficientes; aumenta el acoplamiento
  del almacenamiento.
- **Por qué no**: SQLite puede ser un índice derivado sin sacrificar una fuente
  legible y portable.

### Graphify como memoria completa

- **Ventajas**: una única superficie de consulta para código y conocimiento.
- **Desventajas**: mezcla estructura derivada con decisiones humanas y no
  conserva por sí solo autoridad ni ciclos de aprobación.
- **Por qué no**: contradice el límite establecido en ADR-0003.

### Mantener `docs/context/` sin schema

- **Ventajas**: aprovecha la estructura de v0.3 y no necesita migración.
- **Desventajas**: carece de identificadores, estados, procedencia, activación,
  scopes y validación consistente.
- **Por qué no**: la legibilidad existente no basta para una recuperación
  confiable y gobernada.

## Consecuencias

### Positivas

- La memoria es legible, portable y compatible con Git.
- Claude Code, Codex y futuros adaptadores comparten el mismo formato.
- Graphify puede indexar documentos canónicos sin poseerlos.
- Los índices pueden reemplazarse o reconstruirse sin migrar conocimiento.

### Negativas

- Las consultas eficientes requerirán un índice derivado.
- YAML necesita validación estricta y manejo de errores.
- Muchos documentos pequeños pueden aumentar coste de filesystem.
- La separación versionada/no versionada requiere reglas de Git claras.

### Riesgos

- **Frontmatter inválido**: validar contra JSON Schema antes de indexar.
- **Escrituras parciales**: utilizar create-only y reemplazos atómicos.
- **Duplicados**: buscar antes de crear y usar IDs opacos estables.
- **Fuga accidental a Git**: instalar y verificar un `.gitignore` fail-closed
  para `memory/project/`.
- **Contaminación por propuestas**: excluir `unreviewed`, `rejected`,
  `superseded` y `stale` de los flujos que gobiernan comportamiento.

## Referencias

- [ADR-0003](0003-use-graphify-as-required-cartography.md)
- [Memory Schema](../v1/MEMORY-SCHEMA.md)
- [Behavior Contract, Recuperación](../v1/BEHAVIOR-CONTRACT.md#3-recuperación-de-conocimiento)
