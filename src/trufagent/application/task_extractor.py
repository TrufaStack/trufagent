from __future__ import annotations

import unicodedata
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from trufagent.domain.task import TaskKind, TaskSignals, TaskStrategy


class SignalSource(StrEnum):
    USER = "user"
    INFERRED = "inferred"


class SignalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    value: Any
    source: SignalSource
    confidence: float = Field(ge=0, le=1)
    rationale: str


class IntakeQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    prompt: str
    reason: str


class TaskIntake(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str = Field(min_length=1)
    signal_overrides: dict[str, Any] = Field(default_factory=dict)
    required_symbols: list[str] = Field(default_factory=list)


class TaskExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    signals: TaskSignals
    evidence: list[SignalEvidence] = Field(default_factory=list)
    questions: list[IntakeQuestion] = Field(default_factory=list)
    ready_to_plan: bool
    strategy: TaskStrategy


class TaskExtractionV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    signals: TaskSignals
    evidence: list[SignalEvidence] = Field(default_factory=list)
    questions: list[IntakeQuestion] = Field(default_factory=list)
    ready_to_plan: bool


def _normalized(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(character for character in decomposed if not unicodedata.combining(character))
    return plain.lower()


def _has(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def _infer_kind(text: str) -> tuple[TaskKind, float, str]:
    if _has(
        text,
        "approved plan",
        "approved 12-step plan",
        "plan aprobado",
        "plan de 12",
        "implementation plan",
    ):
        return TaskKind.PLANNED_IMPLEMENTATION, 0.9, "request references an approved plan"
    if _has(text, "redesign", "rediseno", "mockup"):
        return TaskKind.VISUAL_REDESIGN, 0.8, "request is explicitly a redesign"
    if _has(text, "architecture", "arquitectura", "decide how", "decidir como"):
        return TaskKind.ARCHITECTURE, 0.8, "request asks for an architectural decision"
    if _has(
        text,
        "diagnostic commands",
        "comandos de diagnostico",
        "connectivity and environment",
        "conectividad y variables",
    ):
        return TaskKind.DIAGNOSTIC, 0.9, "request is an operational diagnostic"
    if _has(
        text,
        "diagnose",
        "diagnost",
        "corregir",
        "investigate why",
        "investigar por que",
        "cannot ",
        "no puedo",
        "disappear",
        "desapare",
        "not clickable",
        "no funciona",
        "reopens",
        "keeps opening",
    ):
        return TaskKind.BUG, 0.85, "request describes diagnosis or broken behavior"
    if _has(text, "evaluate whether", "evaluar si", "validate hypothesis", "hipotesis"):
        return TaskKind.RESEARCH, 0.8, "request is hypothesis-driven"
    if _has(
        text,
        "badge temporal",
        "temporary badge",
        "fixed dates",
        "fechas fijas",
        "empty-state label",
        "texto de",
        "text of",
    ):
        return TaskKind.SMALL_CHANGE, 0.9, "request is explicit, localized and reversible"
    if _has(text, "implement", "implementar", "allow ", "permitir", "add ", "agregar"):
        return TaskKind.FEATURE, 0.7, "request adds behavior"
    return TaskKind.SMALL_CHANGE, 0.55, "fallback assumes the smallest reversible scope"


def extract_task_signals_v2(intake: TaskIntake) -> TaskExtractionV2:
    text = _normalized(intake.task)
    kind, kind_confidence, kind_reason = _infer_kind(text)
    values: dict[str, Any] = {"kind": kind}
    evidence = [
        SignalEvidence(
            field="kind",
            value=kind.value,
            source=SignalSource.INFERRED,
            confidence=kind_confidence,
            rationale=kind_reason,
        )
    ]

    def infer(field: str, value: Any, confidence: float, rationale: str) -> None:
        values[field] = value
        evidence.append(
            SignalEvidence(
                field=field,
                value=value,
                source=SignalSource.INFERRED,
                confidence=confidence,
                rationale=rationale,
            )
        )

    if kind == TaskKind.BUG and _has(
        text, "diagnose", "investigate why", "investigar por que", "why ", "por que"
    ):
        infer("cause_known", False, 0.85, "request asks to discover the cause")
    elif _has(text, "root cause is", "caused by", "due to", "la causa es"):
        infer("cause_known", True, 0.75, "request states a causal explanation")

    if _has(
        text,
        "database",
        "base de datos",
        "table",
        "tabla",
        "persist",
        "saving",
        "guardado",
        "answers disappear",
    ):
        infer("persistence", True, 0.8, "request touches durable data or save/read flow")
    if _has(text, "silently", "no error", "sin error", "silent"):
        infer("silent_failure", True, 0.85, "failure is described as silent")
    if _has(
        text,
        "both ",
        "ambas ",
        "across ",
        "jobs and archive",
        "week and month",
        "semana y mes",
    ):
        infer("multi_surface", True, 0.8, "request names multiple surfaces")
        if kind == TaskKind.BUG:
            infer(
                "shared_symptom",
                True,
                0.8,
                "the same symptom appears on multiple surfaces; causes remain independent",
            )
    if _has(
        text,
        "shared contract",
        "contrato compartido",
        "all consumers",
        "every consumer",
        "every persistence consumer",
        "each consumer",
        "each persistence consumer",
        "todos los consumidores",
        "cada consumidor",
    ):
        infer("shared_contract", True, 0.85, "request explicitly mentions shared consumers")
    if _has(
        text,
        "decide how",
        "decide the architecture",
        "decidir como",
        "decidir la arquitectura",
        "choose approach",
        "elegir enfoque",
        "interaction pending",
        "interaccion pendiente",
    ):
        infer("open_decisions", True, 0.85, "request explicitly asks for a decision")
    if _has(
        text,
        "authorization",
        "autorizacion",
        "permission rules",
        "reglas de permiso",
        "access control",
        "role matrix",
        "own record",
        "su propio",
        "electricistas",
        "apprentices",
        "aprendices",
    ):
        infer("permissions", True, 0.85, "request changes authorization semantics")
    if _has(
        text,
        "password",
        "contrasena",
        "credential",
        "secret",
        "token",
        "environment variable",
    ):
        infer("secrets", True, 0.9, "request involves secret-bearing diagnostics")
    if _has(text, "production", "produccion"):
        infer("production", True, 0.9, "request explicitly targets production")
    if _has(
        text,
        "approved artifact",
        "artifact design",
        "approved mockup",
        "mockup aprobado",
        "diseno aprobado",
    ):
        infer("approved_artifact", True, 0.9, "an approved external artifact is authoritative")
        available = _has(text, "http://", "https://", "attached", "adjunto", "available at")
        availability_reason = (
            "artifact accessibility is explicit"
            if available
            else "no accessible reference was supplied"
        )
        infer(
            "artifact_available",
            available,
            0.8,
            availability_reason,
        )
    if _has(
        text,
        "mobile",
        "bottom navigation",
        "navegacion movil",
        "ui ",
        "ux ",
        "mockup",
        "pdf",
        "visual",
    ):
        infer("visual", True, 0.75, "request requires rendered or interaction evidence")
    if _has(text, "maplibre", "react-pdf", "library behavior", "comportamiento de la libreria"):
        infer("library_behavior", True, 0.85, "request names behavior owned by a library")
        if kind == TaskKind.BUG and _has(text, "control", "one file", "un archivo"):
            infer("localized", True, 0.75, "library issue names one localized control")
    if _has(text, "state", "status", "stage", "progress", "estado", "etapa"):
        infer("state_logic", True, 0.7, "request changes state-dependent behavior")
    if _has(text, "preview", "integration test", "prueba de integracion"):
        infer("integration_testing", True, 0.8, "request requires integrated execution evidence")
    if _has(
        text,
        "read-only external",
        "external api is read-only",
        "api is read-only",
        "api es read-only",
        "api de solo lectura",
        "external greendeal",
        "greendeal attachments",
    ):
        infer("external_constraint", True, 0.8, "request contains an external constraint")
    if kind == TaskKind.PLANNED_IMPLEMENTATION:
        infer("approved_plan", True, 0.9, "request references an approved implementation plan")
    if kind == TaskKind.RESEARCH and _has(text, "whether", " si ", "hypothesis", "hipotesis"):
        infer(
            "hypothesis_may_negate_work",
            True,
            0.75,
            "research may validly conclude that implementation is unnecessary",
        )
    if kind == TaskKind.SMALL_CHANGE and kind_confidence >= 0.8:
        infer("localized", True, 0.85, "small explicit scope is localized")
        infer("solution_known", True, 0.75, "requested change describes the intended result")

    valid_fields = set(TaskSignals.model_fields)
    unknown = set(intake.signal_overrides) - valid_fields
    if unknown:
        raise ValueError(f"unknown TaskSignals overrides: {', '.join(sorted(unknown))}")
    for field, value in intake.signal_overrides.items():
        values[field] = value
        evidence = [item for item in evidence if item.field != field]
        evidence.append(
            SignalEvidence(
                field=field,
                value=value,
                source=SignalSource.USER,
                confidence=1,
                rationale="explicit user correction",
            )
        )

    signals = TaskSignals.model_validate(values)
    questions: list[IntakeQuestion] = []
    if signals.approved_artifact and not signals.artifact_available:
        questions.append(
            IntakeQuestion(
                field="artifact_available",
                prompt="Provide the approved Artifact URL or accessible project reference.",
                reason="The approved design outranks summaries and cannot be improvised.",
            )
        )
    return TaskExtractionV2(
        task=intake.task,
        signals=signals,
        evidence=evidence,
        questions=questions,
        ready_to_plan=not questions,
    )


def extract_task_signals(intake: TaskIntake) -> TaskExtractionResult:
    from trufagent.application.task_classifier import classify_task

    extraction = extract_task_signals_v2(intake)
    return TaskExtractionResult(
        **extraction.model_dump(),
        strategy=classify_task(extraction.signals),
    )
