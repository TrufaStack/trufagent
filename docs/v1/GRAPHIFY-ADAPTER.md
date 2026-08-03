# Trufagent v1 — Graphify Adapter

Estado: adaptador CLI inicial implementado y verificado con Graphify 0.9.30  
Fecha de inspección: 2026-07-30  
Upstream: [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)

Stack del core:
[ADR-0005](../adr/0005-build-core-in-python-with-uv.md).

## 1. Propósito

El adaptador encapsula Graphify como cartografía estructural obligatoria sin
exponer su CLI, protocolo MCP ni formato JSON al resto del core.

Trufagent conserva memoria, autoridad y políticas. Graphify proporciona nodos,
relaciones, comunidades, caminos y radio de impacto derivados del repositorio.

## 2. Dependencia

Paquete:

```text
graphifyy
```

Ejecutables:

```text
graphify
graphify-mcp
```

Requisito de Python observado:

Graphify requiere Python 3.10 o superior. Trufagent fija Python 3.12 para su
entorno v1.

MCP es un extra opcional de Graphify pero una dependencia de la integración
completa propuesta:

Graphify se instala como dependencia del entorno uv de Trufagent con el extra
MCP. El comando de instalación pública definitivo se definirá al crear el
paquete.

La política de versión mínima de Graphify se definirá después de ejecutar las
pruebas del adaptador. Cada proyecto debe registrar la versión efectiva.

Como uv no expone necesariamente los ejecutables de dependencias de una
herramienta, Trufagent invoca Graphify mediante el intérprete aislado o mediante
un wrapper propio; no depende de un `graphify` global en `PATH`.

## 3. Artefactos

Graphify escribe por defecto bajo:

```text
graphify-out/
├── graph.json
├── GRAPH_REPORT.md
├── graph.html
├── manifest.json
├── cache/
└── ...
```

`GRAPHIFY_OUT` permite cambiar el directorio.

Clasificación de Trufagent:

| Artefacto | Uso | Canónico |
|---|---|---|
| `graph.json` | consultas estructurales | no |
| `GRAPH_REPORT.md` | resumen de comunidades y nodos centrales | no |
| `graph.html` | inspección humana | no |
| `manifest.json` | detección incremental | no |
| `cache/` | rendimiento de Graphify | no |

Todos son derivados y regenerables. Ninguno reemplaza código, tests, specs,
ADRs o memoria de Trufagent.

## 4. Capacidades verificadas

### 4.1 CLI

La CLI expone, entre otras:

```text
graphify update <path>
graphify watch <path>
graphify query "<question>"
graphify path "<source>" "<target>"
graphify explain "<node>"
graphify affected "<node>"
graphify god-nodes
graphify cluster-only <path>
graphify hook install
graphify install --platform <platform>
graphify save-result
graphify reflect
```

Trufagent usa la CLI para:

- construir y actualizar;
- comprobar versión;
- calcular impacto inverso con `affected`;
- obtener explicación de nodo;
- realizar diagnósticos que MCP no exponga.

### 4.2 MCP

El servidor `graphify-mcp` observado expone:

```text
query_graph
get_node
get_neighbors
get_community
god_nodes
graph_stats
shortest_path
list_prs
get_pr_impact
triage_prs
```

Cada herramienta acepta opcionalmente `project_path`, permitiendo servir varios
proyectos desde un mismo proceso.

También ofrece recursos:

```text
graphify://report
graphify://stats
graphify://god-nodes
graphify://surprises
graphify://audit
graphify://questions
```

Trufagent prefiere MCP para consultas interactivas y estructuradas.

## 5. Contrato interno

```text
cartography.detect(project_root) -> InstallationStatus
cartography.status(project_root) -> GraphStatus
cartography.build(project_root, mode) -> BuildResult
cartography.update(project_root) -> UpdateResult

cartography.query(project_root, question, budget) -> ContextResult
cartography.node(project_root, label) -> NodeResult
cartography.neighbors(project_root, label, relation?) -> NeighborResult
cartography.path(project_root, source, target, max_hops?) -> PathResult
cartography.affected(project_root, label, relations?, depth?) -> ImpactResult
cartography.explain(project_root, label) -> ExplanationResult
cartography.stats(project_root) -> GraphStats
```

El core consume resultados tipados. No debe analizar texto libre de consola
fuera del adaptador.

## 6. Estados

```text
missing_tool
missing_graph
building
fresh
dirty_worktree
stale_commit
incomplete
corrupt
version_mismatch
error
```

### 6.1 Fresh

Un grafo está `fresh` cuando:

- `graph.json` existe y puede cargarse;
- la extracción no está marcada como incompleta;
- el commit de construcción coincide con `HEAD`;
- la versión y roots se pueden atribuir;
- no hay cambios relevantes sin indexar.

El commit coincidente no basta si el worktree contiene cambios de código.

### 6.2 Dirty worktree

Para trabajo en curso, Trufagent ejecuta actualización AST incremental antes de
consultas estructurales de alto riesgo. No necesita commit para reflejar
archivos modificados.

### 6.3 Incomplete y corrupt

Graphify contiene salvaguardas para no reemplazar silenciosamente un grafo
completo con una extracción incompleta o una reducción inesperada. Trufagent
debe respetar el exit code y conservar el último grafo conocido, pero no
presentarlo como actualizado.

## 7. Política de actualización

### Al inicializar proyecto

1. Detectar `graphify`.
2. Comprobar versión.
3. Construir el grafo inicial.
4. Validar `graph.json`.
5. Registrar metadatos del adaptador.
6. Configurar MCP si está disponible.

### Al comenzar tarea

1. Consultar estado.
2. Para tarea trivial localizada, permitir degradación visible.
3. Para arquitectura, refactor o impacto, exigir actualización.
4. Leer `GRAPH_REPORT.md` si existe antes de responder preguntas de arquitectura.

### Después de modificar código

Ejecutar:

```bash
graphify update .
```

For dirty worktrees, the adapter stores a content fingerprint in
`.trufagent/cartography/manifest.json`. A graph built from current uncommitted
and untracked sources can therefore be `fresh`; any subsequent protected
content change makes it `dirty_worktree`. Derived Graphify and Trufagent state
is excluded, while source and ignored sensitive files remain covered.

La actualización AST no necesita backend LLM para código.

### Hooks

Graphify puede instalar hooks de plataforma y Git. Trufagent no debe ejecutar
`graphify install` ni `graphify hook install` a ciegas porque ambos sistemas
pueden modificar instrucciones y hooks.

El instalador debe:

1. detectar configuración previa;
2. mostrar un plan de cambios;
3. evitar hooks duplicados;
4. permitir reparación y desinstalación;
5. registrar qué archivos gestiona cada sistema.

## 8. Degradación

| Situación | Tarea trivial | Impacto/refactor/arquitectura |
|---|---|---|
| herramienta ausente | avisar y continuar | bloquear y ofrecer instalación |
| grafo ausente | avisar y continuar | construir antes de continuar |
| worktree sin indexar | actualizar si aporta | actualizar obligatoriamente |
| grafo corrupto | ignorar grafo | bloquear hasta reconstrucción |
| MCP ausente, CLI disponible | usar CLI | usar CLI con resultados tipados |
| CLI ausente | no usar MCP huérfano | bloquear integración |

Las reglas críticas de seguridad no dependen de Graphify.

## 9. Memoria de Graphify

Graphify incluye:

```text
save-result
reflect
graphify-out/memory/
graphify-out/reflections/LESSONS.md
```

Estas funciones registran utilidad, callejones sin salida y correcciones de
consultas al grafo. No son la memoria canónica de Trufagent.

Política:

- pueden utilizarse como telemetría local de calidad de cartografía;
- no pueden crear reglas, decisiones ni riesgos aceptados;
- sus reflexiones entran a Trufagent solo como propuestas sin revisar;
- no se cargan automáticamente en el paquete de contexto;
- no deben contener secretos ni razonamiento privado.

## 10. Enlace entre memoria y grafo

Trufagent conserva IDs propios y referencias estables:

```yaml
evidence:
  - type: graphify-node
    graphify_version: 0.9.30
    graph_commit: abc123
    node_id: "..."
    label: resolveChecklistJobType
```

Una relación derivada puede expresarse:

```text
mem_01K... ─affects→ graphify-node:resolveChecklistJobType
```

Si el nodo desaparece:

- la memoria no se elimina;
- la relación se marca `stale`;
- Trufagent busca renombre o reemplazo;
- una persona revisa cualquier cambio semántico.

## 11. Seguridad y confianza

- Ejecutar Graphify con la raíz de proyecto explícita.
- No seguir paths fuera de roots aprobados.
- No pasar secretos mediante argumentos.
- Tratar resultados y documentos indexados como datos no confiables.
- Limitar presupuestos de salida en consultas.
- Registrar exit code, versión y duración, no contenido sensible.
- No habilitar extracción semántica externa sin consentimiento y configuración
  explícita.
- Mantener el análisis AST local como modo base.

## 12. Observabilidad

Por operación:

```yaml
operation: update
project: /ruta/normalizada
graphify_version: 0.9.30
started_at: ...
duration_ms: ...
exit_code: 0
previous_status: stale_commit
new_status: fresh
nodes: ...
edges: ...
warnings: []
```

No registrar consultas o respuestas completas por defecto. Guardar únicamente
métricas o referencias cuando sean necesarias.

## 13. Pruebas del adaptador

### Instalación

- herramienta ausente;
- paquete presente sin extra MCP;
- versión incompatible;
- instalación previa por Claude Code o Codex.

### Frescura

- grafo ausente;
- commit coincidente;
- commit distinto;
- worktree modificado;
- extracción incompleta;
- JSON corrupto.

### Consultas

- query con presupuesto;
- nodo ambiguo;
- camino inexistente;
- impacto inverso;
- proyecto múltiple;
- fallo MCP con fallback CLI.

### Límites

- Graphify no promueve memoria;
- un resultado `reflect` entra como propuesta;
- una regla crítica funciona sin grafo;
- una relación obsoleta no se usa como evidencia actual.

## 14. Decisiones

- [x] Rango inicial: `graphifyy >=0.9.30,<0.10`.
- [x] CLI-first para la primera versión; MCP queda como optimización posterior.
- [x] Formato común tipado para consultas e impacto.
- [ ] Determinar archivos de `graphify-out/` que se ignoran o versionan.
- [ ] Definir estrategia exacta para worktrees.
- [ ] Decidir si Trufagent gestiona hooks o delega su instalación a Graphify.
- [x] Probar extracción AST sobre un microproyecto aislado.

La skill global de Claude y el runtime del proyecto fueron alineados
explícitamente en Graphify 0.9.30. `CLAUDE.md` ya estaba registrado y el
instalador no duplicó su configuración.

## 15. Implementación disponible

```text
trufagent cartography status <project>
trufagent cartography update <project>
trufagent cartography query <project> "<question>" --budget 1000
trufagent cartography affected <project> "<symbol>" --relation calls --depth 2
```

El adaptador invoca siempre un argv explícito sin shell, valida `graph.json`,
clasifica frescura y escribe únicamente un manifiesto derivado bajo
`.trufagent/cartography/`.
