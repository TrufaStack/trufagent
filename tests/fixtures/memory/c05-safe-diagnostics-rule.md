---
schema: trufagent.memory.v1
id: mem_C05_SAFE_DIAGNOSTICS
kind: rule
title: No imprimir secretos durante diagnósticos
scope: user
status: accepted
trust: human-reviewed
severity: critical
created_at: 2026-07-30T10:15:00+09:30
updated_at: 2026-07-30T10:15:00+09:30
created_by: user
reviewed_by: user
project: "*"
tags: [security, diagnostics]
applies_when:
  concepts: [environment variables, database connectivity]
  paths: []
  symbols: []
  technologies: [fish]
  operations: [shell, read-config]
evidence:
  - type: casebook
    ref: C05
relations:
  affects: []
  caused_by: []
  supersedes: []
  superseded_by: []
  related_to: []
validity:
  valid_from: 2026-07-30
  review_after:
  derived_from_commit:
---
## Rule

Los diagnósticos consultan presencia o estado, nunca valores de credenciales.

## Required actions

- Verificar la shell.
- Redactar salida potencialmente sensible.

## Forbidden actions

- Imprimir archivos `.env`.
- Expandir todas las variables.
