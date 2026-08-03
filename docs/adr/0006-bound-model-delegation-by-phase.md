# ADR-0006: Limitar la delegación de modelos por fases

**Fecha**: 2026-07-31  
**Estado**: superseded by ADR-0007  
**Decisores**: autor de Trufagent y Codex

## Contexto

Trufagent puede reducir coste asignando modelos distintos a exploración,
ejecución y verificación. Sin límites explícitos, varios modelos pueden repetir
trabajo, escribir simultáneamente, contradecir decisiones o gastar más tokens
en coordinación que en resolver la tarea.

La clasificación y `model_route` ya determinan esfuerzo y tier. Falta convertir
esa política en un protocolo ejecutable y auditable sin transferir autoridad
implícita a los modelos delegados.

## Decisión

La delegación se compila como una secuencia de cuatro fases ordenadas:
coordinación, exploración, ejecución y verificación.

- `max_parallel` es uno.
- Cada fase admite como máximo un intento.
- Sólo ejecución puede escribir en el worktree.
- Coordinación, exploración y verificación son de sólo lectura.
- Un tier `none` produce un skip explícito sin modelo ni intento.
- Verificación recibe la evidencia exigida por el plan.
- Los overrides concretos se resuelven por proyecto sin introducir nombres de
  proveedor en la política de dominio.
- Cada invocación genera un evento de uso append-only por sesión. El evento
  contiene modelo, fase, tokens y coste conocido, pero nunca prompts, respuestas
  ni variables de entorno.
- Un límite monetario requiere autorización previa contra un coste estimado. Un
  coste desconocido se etiqueta como tal y nunca se interpreta como cero.

El runtime inicialmente sólo compila protocolos y registra uso. La capacidad de
invocar modelos se habilitará aparte después de canaries específicos.

## Alternativas consideradas

### Delegación paralela por defecto

- **Ventajas**: menor latencia aparente y perspectivas simultáneas.
- **Desventajas**: trabajo duplicado, conflictos de escritura y mayor coste de
  reconciliación.
- **Por qué no**: contradice el objetivo de usar esfuerzo proporcional y hace
  difícil atribuir decisiones.

### Un modelo para toda la tarea

- **Ventajas**: flujo sencillo y menos handoffs.
- **Desventajas**: obliga a elegir entre sobredimensionar tareas pequeñas o
  debilitar fases críticas.
- **Por qué no**: pierde la principal ventaja del routing por fase.

### Guardar transcript completo para auditoría

- **Ventajas**: máxima reconstrucción del razonamiento.
- **Desventajas**: duplica contexto, aumenta exposición de secretos y convierte
  telemetría en una memoria paralela.
- **Por qué no**: la auditoría económica sólo necesita metadatos; las decisiones
  durables pertenecen al sistema de memoria gobernada.

## Consecuencias

### Positivas

- Evita implementaciones y verificaciones duplicadas por construcción.
- Separa autoridad, capacidad del modelo y coste observado.
- Permite auditar consumo sin almacenar contenido sensible.
- Mantiene Graphify y memoria decisional en roles distintos.

### Negativas

- La ejecución serial puede tardar más que un flujo paralelo.
- `max_attempts=1` obliga a volver al coordinador ante un fallo transitorio.
- Los proveedores sin métrica monetaria sólo permiten seguimiento por tokens.

### Riesgos

- **Coste estimado incorrecto**: usar márgenes conservadores y registrar coste
  real cuando exista.
- **Verificador incapaz de operar sin escribir caches**: ejecutar herramientas
  en un sandbox o distinguir artefactos efímeros de cambios al worktree antes de
  habilitar invocaciones.
- **Ledger manipulado**: mantener eventos create-only y validar IDs duplicados;
  añadir encadenamiento criptográfico si el uso deja de ser exclusivamente
  personal.

## Superseded

[ADR-0007](0007-allow-one-supervised-transient-retry.md) preserves serial,
single-writer delegation while allowing one explicitly authorized retry after a
transient provider-process failure.
