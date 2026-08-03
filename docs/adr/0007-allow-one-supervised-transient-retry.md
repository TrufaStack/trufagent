# ADR-0007: Permitir un retry transitorio supervisado

**Fecha**: 2026-07-31  
**Estado**: accepted  
**Decisores**: autor de Trufagent y Codex

## Contexto

ADR-0006 limitó cada fase a un intento para evitar gasto y trabajo duplicado.
Durante el canary shadow, una primera invocación falló sin cambiar el worktree
y una repetición supervisada produjo un handoff válido. Prohibir todo segundo
intento reduce fiabilidad; reintentar automáticamente cualquier error debilita
los gates.

## Decisión

Trufagent permite exactamente un segundo intento únicamente cuando el fallo es
transitorio y pertenece al proceso del provider, el fingerprint protegido no
cambió, el presupuesto fue reautorizado y una persona confirmó el retry.

Respuesta inválida, gate de aceptación fallido, evidencia ausente, cambio del
worktree y presupuesto agotado no son retryables. El segundo intento usa un
invocation ID nuevo y vuelve a atravesar todos los gates.

## Alternativas consideradas

### Mantener un intento absoluto

- **Ventajas**: coste y flujo máximamente predecibles.
- **Desventajas**: convierte fallos transitorios inocuos en bloqueos.
- **Por qué no**: el canary real demostró una pérdida de fiabilidad evitable.

### Reintentar automáticamente errores transitorios

- **Ventajas**: recuperación sin intervención.
- **Desventajas**: clasificación imperfecta, gasto silencioso y riesgo de
  repetir una acción cuyo estado no conocemos.
- **Por qué no**: contradice la autoridad humana y el presupuesto explícito.

## Consecuencias

### Positivas

- Recupera fallos transitorios sin abrir retries generales.
- Conserva atribución y presupuesto por invocación.
- Mantiene ejecución serial y single-writer.

### Negativas

- Requiere confirmación humana y una segunda autorización presupuestaria.
- El host debe distinguir fallo de proceso de respuesta inválida.

### Riesgos

- **Clasificación optimista**: sólo `transient-process` es elegible.
- **Estado parcial**: fingerprint idéntico es obligatorio.
- **Retry repetido**: `prior_attempts` debe ser exactamente uno y el intento
  autorizado es siempre el número dos.
