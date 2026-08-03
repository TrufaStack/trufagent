# Phase 36 — V2 routing matrix

## Objetivo

Demostrar que el comando real `trufagent prepare` conserva una política compacta
y explicable al combinar clasificación, nivel de modelo, Graphify y skills por
fase.

## Matriz cubierta

| Escenario | Complejidad | Tier | Skills por fase | Graphify |
| --- | --- | --- | --- | --- |
| Cambio pequeño localizado | low | economy | ninguna | abstención |
| Fix conocido y localizado | low | economy | implementación, verificación | abstención |
| Fix con causa desconocida y persistencia | high | frontier | exploración, implementación, verificación | consulta |
| Feature entendida | medium | balanced | implementación, verificación | abstención |
| Arquitectura con decisiones abiertas | high | frontier | exploración | consulta |
| Investigación | high | frontier | ninguna | consulta |

Los tiers se resuelven mediante el perfil del proyecto: `economy` corresponde a
Luna con esfuerzo `max`; `balanced` y `frontier`, a Sol con esfuerzo `low`.

## Método

`tests/test_prepare_routing_matrix.py` invoca la entrada CLI real con intakes
temporales y un catálogo revisado controlado. Solo sustituye el límite externo
de Graphify por un adaptador determinista, de modo que la prueba pueda afirmar
tanto la presencia de referencias estructurales como la abstención.

## Aceptación

- cada escenario devuelve tipo, complejidad y tier esperados;
- las skills aparecen en orden y con `explore`, `implement` o `verify`;
- Graphify solo se consulta cuando la política declara contexto estructural útil;
- el contrato JSON de `prepare` expone la fase sin cargar cuerpos de skills.
