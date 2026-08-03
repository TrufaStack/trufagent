# Trufagent v1 — Product Brief

Estado: borrador de trabajo aprobado como línea base  
Fecha: 2026-07-30  
Usuario inicial: el autor de Trufagent

## Capacidad

Trufagent es un asistente personal de desarrollo que entrega a cada tarea
solamente el contexto, el método y el esfuerzo de IA necesarios. Conserva las
decisiones importantes de cada proyecto, localiza rápidamente el código y los
artefactos relevantes, selecciona skills confiables y ajusta la profundidad de
exploración, ejecución y verificación.

La primera versión se probará con trabajo real del autor. No se optimizará para
distribución pública hasta que su comportamiento resulte predecible y útil en
uso cotidiano.

## Problema

Los asistentes de desarrollo suelen desperdiciar esfuerzo de dos maneras:

1. Aplican demasiada ceremonia a tareas pequeñas o demasiado poca investigación
   a tareas riesgosas.
2. Releen grandes partes del repositorio o pierden decisiones, restricciones,
   diseños y lecciones de sesiones anteriores.

Esto produce planes innecesarios, recorridos costosos de código, repetición de
errores, decisiones contradictorias y retrabajo por utilizar una fuente de
verdad incompleta.

## Promesa

> Trufagent asigna la inteligencia adecuada y le entrega únicamente el contexto
> necesario.

Para cumplirla, Trufagent debe:

- recordar decisiones, razones, reglas, riesgos y estado;
- encontrar estructuras, dependencias, símbolos y artefactos relevantes;
- seleccionar el método de trabajo apropiado mediante skills confiables;
- asignar por separado esfuerzo de exploración, ejecución y verificación;
- convertir ciertos aprendizajes en protecciones verificables;
- explicar brevemente por qué eligió su estrategia;
- producir evidencia suficiente antes de declarar una tarea terminada.

## Usuario y contexto inicial

El usuario inicial es un desarrollador individual que trabaja principalmente con
Claude Code y Codex en proyectos reales. Es el tester principal y acepta que v1
sea local, explícita y algo técnica mientras se valida la tesis.

El diseño debe permitir portabilidad futura, pero esa portabilidad no justifica
construir ahora una plataforma pública.

## Pilares del producto

### 1. Conocimiento

Mantener conocimiento durable, inspeccionable y con procedencia:

- reglas;
- hechos del entorno;
- decisiones y decisiones negativas;
- riesgos e incidentes;
- lecciones verificadas;
- artefactos externos;
- hechos estructurales;
- estado temporal y resúmenes de sesión.

La conversación completa no es memoria y una inferencia del agente no es
automáticamente verdad.

### 2. Cartografía

Usar Graphify como mapa estructural obligatorio para reducir el espacio de
búsqueda:

- módulos y dependencias;
- símbolos y consumidores;
- endpoints, servicios y persistencia;
- componentes y superficies;
- decisiones y riesgos relacionados.

El grafo es una caché derivada. El código y las pruebas continúan siendo la
fuente de verdad. La memoria gobernada pertenece a Trufagent, no a Graphify.

### 3. Política de esfuerzo

Asignar presupuestos independientes a:

- exploración;
- ejecución;
- verificación.

El tamaño aparente de una tarea no determina por sí solo su riesgo ni la
evidencia necesaria.

### 4. Skills

Tratar las skills como conocimiento procedimental versionado. Seleccionar el
conjunto mínimo que cubra la tarea y registrar su utilidad.

Las skills descargadas de terceros requieren procedencia, revisión y permisos
conocidos. La biblioteca completa no debe competir por activarse en cada tarea.

### 5. Ejecución portable

Expresar necesidades como capacidades abstractas y resolverlas mediante
adaptadores:

- Claude Code;
- Codex;
- LiteLLM/BYOK en una etapa posterior.

El núcleo no debe depender de nombres concretos de modelos.

## Principios

1. No usar un mazo para matar una mosca.
2. Diagnosticar antes de modificar cuando la causa no esté demostrada.
3. Recuperar contexto antes de planificar.
4. Planificar en detalle lo conocido y experimentar explícitamente sobre lo
   desconocido.
5. Una decisión peligrosa necesita protección, no solamente documentación.
6. Las reglas críticas se aplican antes de ejecutar herramientas.
7. El conocimiento derivado dirige hacia evidencia; no la sustituye.
8. No construir también es un resultado válido si la evidencia invalida la
   hipótesis.
9. La iniciativa fuera de alcance debe respetar límites de riesgo y autonomía.
10. Toda estrategia debe poder explicarse y corregirse.

## Antiobjetivos de v1

- Ser un producto público o marketplace.
- Operar de forma autónoma indefinida.
- Guardar transcripciones completas.
- Aprender reglas automáticamente a partir de hábitos.
- Depender de muchas API keys.
- Mantener una flota grande permanentemente activa.
- Reconstruir el dashboard antes de validar la política.
- Sustituir Git, tests, documentación canónica o revisión humana.
- Convertir el grafo derivado de Graphify en memoria canónica.
- Optimizar precios de modelos antes de medir el comportamiento.

## Experiencia inicial

Una entrada principal:

```text
/trufagent <tarea>
```

Antes de actuar, Trufagent comunica de forma breve:

```text
Estrategia: ejecución conocida con verificación alta.
Contexto: regla de integración read-only y ADR-004.
Skills: writing-plans y TDD.
Motivo: cinco cambios dependientes con diseño técnico aprobado.
```

El usuario puede corregir la selección:

```text
/trufagent --direct
/trufagent --standard
/trufagent --deep
/trufagent --use <skill>
/trufagent --without <skill>
```

La sintaxis definitiva permanece abierta; el contrato de comportamiento no debe
depender de ella.

## Métricas personales

Por tarea:

- estrategia y presupuestos elegidos;
- correcciones manuales del usuario;
- contexto y skills seleccionados;
- número de delegaciones;
- duración;
- tests, previews y otras evidencias;
- rework posterior;
- coste o tokens cuando estén disponibles;
- valoración: insuficiente, adecuado o excesivo.

Métrica principal:

> Porcentaje de tareas resueltas correctamente sin corregir el nivel de
> esfuerzo ni rehacer decisiones ya aprobadas.

Métricas secundarias:

- incidentes repetidos;
- decisiones recuperadas correctamente;
- skills seleccionadas que aportaron valor;
- tareas donde investigar evitó una implementación;
- barridos de código evitados o correctamente justificados;
- conocimiento propuesto, aceptado, rechazado y supersedido.

## Riesgos

- La clasificación puede sonar razonable y aun así elegir esfuerzo incorrecto.
- Una memoria incorrecta puede contaminar sesiones futuras.
- Un mapa obsoleto puede ocultar consumidores relevantes.
- Demasiadas skills pueden provocar solapamiento o instrucciones conflictivas.
- La instrumentación puede añadir más ceremonia de la que ahorra.
- Los adaptadores pueden divergir y producir comportamientos distintos.
- Una política escrita solo como prompt puede ser ignorada.

## Criterio de éxito para la fase personal

Trufagent estará listo para considerar un relanzamiento cuando:

- se use de forma sostenida en proyectos reales;
- las decisiones de esfuerzo sean mayoritariamente aceptadas sin corrección;
- no repita incidentes críticos ya registrados;
- recupere diseños y decisiones aplicables antes de implementar;
- el registro de memoria se mantenga pequeño, trazable y útil;
- las skills activadas muestren valor observable;
- el autor prefiera trabajar con Trufagent frente al flujo base.

## Decisiones abiertas

1. Estrategia de frescura, invalidación y regeneración de Graphify.
2. Primer adaptador de referencia: Claude Code o Codex.
3. Cómo medir tokens de forma comparable entre plataformas.
4. Cuándo promover una lección recurrente a regla o skill.

## Handoff

El comportamiento esperado está definido en
[`BEHAVIOR-CONTRACT.md`](./BEHAVIOR-CONTRACT.md). Los casos reales que deben
validarlo están en [`CASEBOOK.md`](./CASEBOOK.md).

El runtime v1 está implementando su primera línea vertical en Python 3.12 con
uv, según [ADR-0005](../adr/0005-build-core-in-python-with-uv.md). Memoria,
cartografía, clasificación y selección mínima de skills ya producen un
`TaskPlan` auditable a partir de señales explícitas.
