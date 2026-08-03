# ADR-0002: Bloquear exposición de secretos por defecto

**Fecha**: 2026-07-30  
**Estado**: accepted  
**Decisores**: autor de Trufagent y Codex

## Contexto

Comandos de diagnóstico pueden imprimir archivos de configuración, expandir
variables o mostrar URLs con credenciales. El proyecto de referencia sufrió
exposición de la misma contraseña en tres sesiones, incluyendo un incidente
provocado por usar sintaxis Bash en un entorno fish. Una advertencia textual no
evitó la recurrencia.

## Decisión

Trufagent bloquea por defecto comandos conocidos por imprimir archivos de
entorno completos, expandir credenciales o exponer configuraciones sensibles.
Antes de producir comandos dependientes de shell, verifica el entorno de
ejecución.

Una anulación requiere mostrar la clase de riesgo, demostrar que no existe una
alternativa segura y recibir confirmación explícita para esa ejecución. La
confirmación no crea un permiso permanente y el registro no conserva comandos,
salidas ni valores sensibles.

Si una plataforma no puede imponer técnicamente el bloqueo, el adaptador debe
degradar de forma visible a confirmación obligatoria; no puede fingir una
garantía.

## Alternativas consideradas

### Advertir y continuar

- **Ventajas**: menor fricción y compatibilidad simple con cualquier plataforma.
- **Desventajas**: depende de atención y memoria; no evita ejecuciones
  accidentales.
- **Por qué no**: el historial demuestra que las advertencias no impiden
  incidentes repetidos.

### Prohibir sin excepciones

- **Ventajas**: límite simple y máxima protección preventiva.
- **Desventajas**: puede impedir diagnósticos excepcionales legítimos cuando no
  existe alternativa.
- **Por qué no**: se necesita una vía explícita y limitada para casos
  extraordinarios.

## Consecuencias

### Positivas

- La seguridad se aplica antes de usar herramientas.
- Los incidentes conocidos se convierten en protección ejecutable.
- La anulación queda limitada a una operación consciente.

### Negativas

- Requiere análisis de comandos específico por shell y plataforma.
- Puede producir falsos positivos.
- Algunas plataformas solo podrán exigir confirmación, no bloquear.

### Riesgos

- **Bypass por sintaxis desconocida**: combinar patrones, clasificación de
  operación y pruebas adversariales.
- **Registro sensible**: almacenar solamente clase de riesgo y resultado de la
  decisión.
- **Confianza excesiva**: presentar el filtro como defensa en profundidad, no
  como detector perfecto de secretos.

## Referencias

- [Behavior Contract, A-03 a A-06](../v1/BEHAVIOR-CONTRACT.md#a-03--seguridad-crítica)
- [Casebook, C05](../v1/CASEBOOK.md#c05--fugas-de-contraseña-en-terminal)
- [Memory Schema, ejemplo de regla segura](../v1/MEMORY-SCHEMA.md#161-regla-de-diagnóstico-seguro)
