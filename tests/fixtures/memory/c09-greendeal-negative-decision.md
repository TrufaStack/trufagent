---
schema: trufagent.memory.v1
id: mem_C09_GREENDEAL_CACHE
kind: negative_decision
title: No cachear attachments de GreenDeal
scope: team
status: accepted
trust: externally-verified
severity: medium
created_at: 2026-07-30T10:15:00+09:30
updated_at: 2026-07-30T10:15:00+09:30
created_by: user
reviewed_by: user
project: jc-app
tags: [greendeal, attachments, read-only]
applies_when:
  concepts: [GreenDeal attachments, expiring links]
  paths: []
  symbols: []
  technologies: [GreenDeal API, S3]
  operations: [read, cache]
evidence:
  - type: external-test
    ref: 8+ historical jobs returned HTTP 200
relations:
  affects: []
  caused_by: []
  supersedes: []
  superseded_by: []
  related_to: []
validity:
  valid_from: 2026-07-30
  review_after: 2027-01-30
  derived_from_commit:
---
## Hypothesis

Los enlaces de attachments de GreenDeal expiran.

## Decision

No implementar cache ni proxy local.

## Reopen when

Aparezcan respuestas 403, URLs firmadas o cambios documentados en la API.
