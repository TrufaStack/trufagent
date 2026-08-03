# ADR-0005: Implementar el core en Python y distribuirlo con uv

**Fecha**: 2026-07-30  
**Estado**: accepted  
**Decisores**: autor de Trufagent y Codex

## Contexto

Trufagent necesita un core portable para memoria, clasificación, selección de
skills y cartografía. Graphify ya requiere Python y el dashboard existente usa
FastAPI. Añadir otro runtime aumentaría instalación y mantenimiento sin eliminar
Python ni mejorar el principal coste del sistema, que será contexto, modelos y
operaciones de I/O.

## Decisión

Trufagent implementa su core v1 en Python 3.12 y usa `uv` para entorno,
lockfile, instalación y distribución.

El stack inicial es:

- Pydantic v2 para modelos, validación y generación de JSON Schema;
- PyYAML para frontmatter de la memoria canónica;
- SQLite FTS5 como índice derivado;
- pytest para contratos, fixtures y Casebook;
- Graphify encapsulado por el adaptador dentro del entorno de Trufagent;
- CLI delgada, sin servidor permanente;
- FastAPI reservado para recuperar el dashboard posteriormente.

Trufagent no importa internals privados de Graphify. Lo invoca mediante su
superficie pública de módulo, CLI o MCP y traduce resultados a contratos
internos tipados.

## Alternativas consideradas

### TypeScript

- **Ventajas**: ecosistema fuerte para plugins, CLI y UI.
- **Desventajas**: añade Node sin eliminar Python; duplica tooling y modelos.
- **Por qué no**: no mejora el cuello de botella principal y complica la
  distribución personal.

### Go

- **Ventajas**: binario único, startup rápido y bajo consumo.
- **Desventajas**: Graphify seguiría ejecutándose en Python; aumenta el trabajo
  de integración y duplica runtimes.
- **Por qué no**: puede reconsiderarse como wrapper futuro si existe evidencia
  de problemas de distribución.

### Rust

- **Ventajas**: máximo control de rendimiento y memoria.
- **Desventajas**: mayor coste de desarrollo y ninguna eliminación de la
  dependencia Python.
- **Por qué no**: optimiza un cuello de botella todavía no observado.

### Shell

- **Ventajas**: prototipado inicial rápido.
- **Desventajas**: diferencias entre fish, Bash, PowerShell y cmd; tipado,
  validación y seguridad insuficientes.
- **Por qué no**: contradice los requisitos de portabilidad y prevención de
  exposición de secretos.

## Consecuencias

### Positivas

- Un runtime compartido por core, Graphify y dashboard.
- Desarrollo rápido con contratos tipados.
- Instalación reproducible y aislada mediante uv.
- SQLite disponible en la librería estándar.
- JSON Schema generado desde modelos del runtime.

### Negativas

- No existe inicialmente un binario nativo único.
- Startup y memoria serán mayores que en Go o Rust.
- Hay que gestionar versiones e intérpretes Python.
- `uv tool install` no expone necesariamente ejecutables aportados por
  dependencias.

### Riesgos

- **Acoplamiento a Graphify**: mantener toda interacción detrás del adaptador.
- **Entorno roto**: fijar versiones con lockfile y ofrecer doctor/repair.
- **Ejecutable Graphify ausente del PATH**: invocar el módulo con el intérprete
  aislado o exponer un wrapper `trufagent graph`.
- **Crecimiento del dashboard dentro del core**: mantener FastAPI fuera del
  runtime mínimo hasta validar el motor.
- **Optimización prematura**: medir startup, memoria y tiempos antes de mover
  componentes a otro lenguaje.

## Condición de revisión

Reconsiderar Go o un binario exterior únicamente si mediciones reales muestran
problemas de startup, consumo, instalación o distribución que Python y uv no
resuelven.

## Referencias

- [ADR-0003](0003-use-graphify-as-required-cartography.md)
- [ADR-0004](0004-use-markdown-yaml-as-canonical-memory.md)
- [Graphify Adapter](../v1/GRAPHIFY-ADAPTER.md)
- [Memory Schema](../v1/MEMORY-SCHEMA.md)
