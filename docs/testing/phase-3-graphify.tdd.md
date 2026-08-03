# Fase 3 — Evidencia TDD del adaptador Graphify

Fecha: 2026-07-30

## Alcance

- `GraphifyAdapter` CLI-first detrás de `CartographyPort`;
- detección de grafo ausente, corrupto, incompleto, obsoleto y worktree sucio;
- actualización AST y manifiesto derivado;
- consultas con presupuesto nativo;
- impacto inverso con relaciones explícitas;
- parsing tipado de líneas `NODE` y `EDGE`;
- cartografía separada de memoria gobernante en el context packet;
- comandos CLI de Trufagent.

## RED

Las pruebas iniciales fallaron durante colección porque
`trufagent.infrastructure.graphify_adapter` aún no existía.

## GREEN

La suite completa terminó con 29 pruebas aprobadas. La cobertura focalizada de
cartografía y contexto fue 96% sobre 225 statements.

## Smoke real

Se creó un microproyecto Python aislado en `/tmp` y se ejecutó Graphify 0.9.30:

```text
Rebuilt: 3 nodes, 3 edges, 1 communities
```

Después, `trufagent cartography status` devolvió `fresh` y una consulta con
presupuesto 200 produjo tres nodos tipados y dos relaciones:

```text
app.py --contains--> save_checklist()
save_checklist() --calls--> persist_job()
```

No se instalaron hooks, skills ni configuración de plataforma.

Durante el smoke, Graphify escribió un `graphify-out/manifest.json` relativo al
directorio de invocación aunque el grafo se generó correctamente bajo el target
de `/tmp`. El artefacto fue inspeccionado y retirado; Trufagent no usa ese
manifest como fuente de frescura y conserva su propio manifiesto derivado.

## Propiedades verificadas

- Ningún comando utiliza shell.
- La raíz del proyecto se normaliza antes de ejecutar.
- `query` transmite el presupuesto a Graphify.
- Un grafo no consultable falla explícitamente.
- El manifiesto es derivado; `graph.json` sigue siendo propiedad de Graphify.
- Los resultados estructurales no entran a la lista de memoria gobernante.
