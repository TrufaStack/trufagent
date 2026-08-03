---
schema: trufagent.memory.v1
id: mem_C02_CHECKLIST_RISK
kind: risk
title: No confundir el tipo real de job con el bucket de plantilla
scope: team
status: accepted
trust: code-verified
severity: high
created_at: 2026-07-30T10:15:00+09:30
updated_at: 2026-07-30T10:15:00+09:30
created_by: user
reviewed_by: user
project: jc-app
tags: [checklist, persistence]
applies_when:
  concepts: [checklist persistence, job type]
  paths: [src/api/**]
  symbols: [resolveChecklistJobType]
  technologies: []
  operations: [write]
evidence:
  - type: casebook
    ref: C02
relations:
  affects: [resolveChecklistJobType]
  caused_by: []
  supersedes: []
  superseded_by: []
  related_to: []
validity:
  valid_from: 2026-07-30
  review_after:
  derived_from_commit:
---
## Risk

El bucket usado para elegir una plantilla no identifica dónde persiste el tipo
real del job.

## Required actions

- Buscar todos los consumidores del símbolo.
- Verificar la tabla real de escritura.
- Añadir regresión por tipo de job.
