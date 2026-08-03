# Trufagent v2 — Product Brief

## Propósito

Trufagent ayuda a un agente de desarrollo a resolver tareas con el mínimo
contexto y coste necesarios.

Antes del trabajo, recupera contexto útil desde memoria Markdown y Graphify,
estima la complejidad de la tarea y recomienda un comportamiento y un nivel de
modelo. Después de que el cambio haya sido implementado, verificado y
confirmado mediante merge, resume el resultado y propone qué conocimiento o
cartografía conviene actualizar.

Trufagent no pretende reemplazar al agente anfitrión ni convertirse en un
orquestador general de agentes.

## Ciclo esencial

1. Entender la solicitud del usuario.
2. Clasificar la tarea y estimar su complejidad.
3. Recuperar solamente el contexto necesario:
   - decisiones o hechos compactos desde una memoria ágil y accesible;
   - estructura, símbolos e impacto desde Graphify.
4. Seleccionar las skills que aporten el comportamiento necesario.
5. Recomendar nivel de modelo y esfuerzo para explorar, implementar y verificar.
6. Dejar que Codex, Claude Code u otro anfitrión ejecute el trabajo.
7. Confirmar que la implementación y sus verificaciones terminaron.
8. Esperar confirmación del merge antes de consolidar conocimiento durable.
9. Producir un resumen y proponer:
   - nueva memoria o actualización de memoria existente;
   - consolidación o retiro de memoria que haya quedado obsoleta;
   - regeneración del grafo cuando cambió la estructura confirmada.

Durante todo el ciclo, la memoria debe mantenerse pequeña, fácil de consultar y
orientada a decisiones útiles. Incorporar conocimiento nuevo no debe degradar
su accesibilidad ni obligar a cargar historial irrelevante.

## Capacidades obligatorias del MVP

### Intake compacto

Trufagent distingue inicialmente entre:

- cambio pequeño;
- fix;
- feature;
- investigación;
- arquitectura.

La clasificación debe usar pocas señales explicables. No debe exigir una matriz
extensa de campos para tareas comunes.

### Contexto económico

La memoria contiene decisiones, restricciones y hechos durables en Markdown.
Graphify responde preguntas estructurales sobre el código. Trufagent combina
ambas fuentes dentro de un presupuesto explícito y permite abstenerse cuando
ninguna aporta valor.

La memoria debe permanecer ágil: entradas breves, búsqueda económica,
procedencia clara y mecanismos simples para actualizar, consolidar o retirar
contenido obsoleto. Su utilidad se mide por la rapidez con que entrega contexto
relevante, no por la cantidad de información acumulada.

El contexto cargado debe ser relevante, trazable y menor que una exploración
general del repositorio.

### Enrutamiento de modelos

Trufagent recomienda uno de tres niveles:

| Nivel | Uso esperado |
| --- | --- |
| `economy` | Tarea clara, localizada y de bajo riesgo |
| `balanced` | Implementación normal con exploración o impacto moderado |
| `frontier` | Alta ambigüedad, arquitectura, diagnóstico difícil o riesgo alto |

La recomendación orienta al anfitrión; no inicia por sí sola otros modelos ni
procesos.

Perfiles Codex iniciales:

| Nivel | Modelo | Reasoning effort |
| --- | --- | --- |
| `economy` | GPT-5.6-Luna | `max` |
| `balanced` | GPT-5.6-Sol | `low` |
| `frontier` | GPT-5.6-Sol | `low` |

El tier expresa una política de coste y comportamiento, no una escala lineal de
potencia. `models resolve` traduce el tier al perfil concreto del anfitrión y
expone tanto modelo como reasoning effort.

### Selección proporcional de skills

Las skills aportan conocimiento procedimental: depuración, planificación, TDD,
diseño visual u otros comportamientos especializados. Trufagent selecciona el
conjunto mínimo que cubra la tarea y explica brevemente el motivo.

La necesidad semántica decide **qué** skill corresponde; la complejidad decide
**cuánta** metodología conviene cargar:

| Complejidad | Comportamiento esperado |
| --- | --- |
| Baja | Trabajar directamente; cargar una skill solo si es claramente necesaria |
| Media | Cargar las skills relevantes para la incertidumbre y la verificación |
| Alta | Combinar skills complementarias cuando reduzcan riesgo o ambigüedad |

Ejemplos iniciales:

- bug con causa desconocida: depuración sistemática;
- decisiones de producto o arquitectura abiertas: brainstorming;
- solución entendida con pasos dependientes: planificación;
- fix confirmado o lógica sensible: TDD proporcional;
- cambio de interfaz: skill visual o de UI/UX.

Trufagent consulta primero metadatos compactos y carga las instrucciones
completas solamente después de seleccionar una skill. El usuario puede forzar o
excluir skills. El catálogo completo no debe ocupar el contexto inicial ni
competir por activarse en cada tarea.

La biblioteca se actualiza desde las skills instaladas de Codex, Claude y sus
plugins. Conserva variantes por anfitrión, permite buscar capacidades por nombre
y descripción, y exige revisión antes de una selección automática. Su contrato
se detalla en `SKILL-LIBRARY.md`.

### Comportamiento por fase

Cada tarea recibe presupuestos simples para:

- exploración;
- implementación;
- verificación.

Los niveles iniciales son `none`, `low`, `medium` y `high`. El anfitrión conserva
la coordinación, las herramientas y la autoridad para modificar el proyecto.

Cada skill recomendada declara además cuándo debe cargarse: `explore`,
`implement` o `verify`. Una selección manual usa `any`, porque Trufagent no debe
inventar la intención temporal del usuario. Así, una skill necesaria para
revisar el resultado no consume contexto durante la exploración.

### Cierre posterior al merge

El cierre genera un resumen compacto con:

- cambio realizado;
- verificaciones relevantes;
- decisiones nuevas o corregidas;
- propuesta de memoria;
- necesidad de regenerar Graphify.

Las propuestas de memoria requieren aceptación humana. El grafo es un artefacto
derivado y puede regenerarse a partir del repositorio confirmado.

## Interfaces del MVP

Trufagent ofrece un runtime compartido y adaptadores delgados para Codex y
Claude Code. Los adaptadores traducen la interacción nativa al mismo ciclo
esencial; no duplican políticas ni implementan un segundo orquestador.

Una preparación de tarea debería poder expresarse de forma aproximada como:

```yaml
task: fix
complexity: medium
model_tier: balanced
skills:
  - name: systematic-debugging
    phase: explore
context:
  memories:
    - authentication-decisions
  graph:
    symbols:
      - AuthService
      - TokenRepository
effort:
  explore: medium
  implement: medium
  verify: high
```

Después del merge:

```yaml
summary: Se corrigió la renovación concurrente de tokens.
memory_proposals:
  - La renovación se serializa por usuario.
graph:
  refresh: true
```

Los formatos definitivos pueden evolucionar. Estos ejemplos describen la
información necesaria, no un contrato completo de implementación.

## Capacidades diferidas

Las siguientes capacidades quedan fuera del MVP y no deben condicionar su
diseño:

- ejecución shadow mediante procesos anidados;
- delegación automática o protocolos multiagente;
- reintentos supervisados entre proveedores;
- promoción, pilotos y workspaces de aprobación;
- contabilidad detallada de intentos, tokens o costes;
- cuarentenas y sellos para estados intermedios;
- clasificación exhaustiva de riesgos mediante numerosos booleanos;
- políticas específicas para cada proveedor o caso de evaluación.

La selección básica de skills sí pertenece al MVP. Quedan diferidos los
catálogos con gobernanza extensa, métricas históricas de utilidad y políticas
detalladas de permisos o promoción.

Podrán reconsiderarse después de validar el ciclo esencial con proyectos
reales. Hasta entonces, deben permanecer separadas o eliminarse de la ruta
principal.

## Principios de diseño

- Menos contexto es mejor cuando conserva la información necesaria.
- La memoria debe ser ágil, accesible y fácil de mantener vigente.
- La complejidad de Trufagent debe ser menor que la complejidad que evita.
- La memoria gobierna decisiones durables; Graphify describe estructura actual.
- El anfitrión coordina y ejecuta; Trufagent prepara y aprende.
- Las recomendaciones deben ser explicables con pocas señales.
- Las skills se activan por necesidad y de forma proporcional a la complejidad.
- Ningún mecanismo avanzado pertenece al núcleo antes de demostrar su necesidad.
- El merge confirmado separa conocimiento provisional de conocimiento durable.

## Criterios de éxito

El MVP se considera útil cuando puede:

1. preparar fixes y features reales con menos contexto que una exploración libre;
2. seleccionar de forma razonable entre `economy`, `balanced` y `frontier`;
3. seleccionar skills mínimas y pertinentes según tarea y complejidad;
4. recuperar memoria relevante de forma rápida, compacta y trazable;
5. entregar contexto con referencias a memoria y archivos o símbolos del grafo;
6. mantener adaptadores equivalentes y pequeños para Codex y Claude Code;
7. cerrar un cambio merged con un resumen y propuestas revisables;
8. actualizar la cartografía sin convertirla en fuente de decisiones;
9. funcionar sin delegación, shadow execution, promoción ni ledgers detallados.

## No objetivos

Trufagent v2 no busca:

- reemplazar la planificación o coordinación nativa del anfitrión;
- ejecutar una flota de agentes;
- garantizar por sí solo la seguridad de producción;
- modelar todas las clases posibles de tarea o riesgo;
- conservar prompts, respuestas o razonamiento privado;
- convertir cada sesión en conocimiento permanente;
- optimizar proveedores antes de validar el flujo básico del producto.

## Próxima decisión

Mapear cada subsistema de v1 a una de cuatro acciones:

- conservar;
- simplificar;
- aislar como experimental;
- retirar.

Ese mapa debe preceder cualquier poda de código y mantener el ciclo esencial
operativo durante la transición.
