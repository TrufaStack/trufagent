# ADR-0001: Limitar autonomía sobre bugs incidentales

**Fecha**: 2026-07-30  
**Estado**: accepted  
**Decisores**: autor de Trufagent y Codex

## Contexto

La verificación de una tarea puede revelar bugs preexistentes no incluidos en el
pedido. Corregirlos inmediatamente puede evitar daño y retrabajo, pero también
puede expandir silenciosamente el alcance hacia cambios que el usuario no
autorizó. Trufagent necesita conservar iniciativa sin asumir autoridad sobre
áreas riesgosas.

## Decisión

Trufagent puede corregir un bug incidental sin detenerse solamente cuando es
reproducible, su causa está confirmada, el cambio es localizado, reversible y
verificable, y resulta necesario para validar la tarea actual o evitar daño
evidente.

La corrección automática no está permitida si afecta autenticación, datos
históricos, infraestructura, producción o contratos externos. En esos casos,
Trufagent documenta el hallazgo, clasifica su severidad y solicita autorización.

## Alternativas consideradas

### Nunca corregir bugs fuera del pedido

- **Ventajas**: alcance totalmente predecible y control humano constante.
- **Desventajas**: interrumpe innecesariamente el trabajo y puede dejar defectos
  confirmados que bloquean una verificación.
- **Por qué no**: elimina iniciativa útil incluso en correcciones locales de
  bajo riesgo.

### Corregir todo bug confirmado

- **Ventajas**: maximiza la cantidad de defectos resueltos durante una sesión.
- **Desventajas**: permite expansión silenciosa, aumenta el radio de cambio y
  puede introducir modificaciones sensibles sin autorización.
- **Por qué no**: confirmar una causa no concede autoridad para modificar
  cualquier superficie afectada.

## Consecuencias

### Positivas

- Conserva autonomía útil para hallazgos locales y seguros.
- Establece un límite comprensible y auditable.
- Separa la evidencia de la tarea original y la del bug incidental.

### Negativas

- Requiere evaluar riesgo y reversibilidad antes de actuar.
- Algunos bugs claros necesitarán una pausa de autorización.
- La clasificación puede variar entre adaptadores si no comparten contrato.

### Riesgos

- **Clasificación optimista**: mitigar con criterios code-gated y escalado
  conservador ante dudas.
- **Expansión acumulativa**: registrar cada hallazgo como unidad separada y
  reevaluar el presupuesto de la tarea.
- **Diferencias de plataforma**: mantener la política en el core, no en prompts
  específicos del adaptador.

## Referencias

- [Behavior Contract, A-02](../v1/BEHAVIOR-CONTRACT.md#a-02--hallazgos-incidentales)
- [Casebook, C11](../v1/CASEBOOK.md#c11--bugs-incidentales-en-post-install)
