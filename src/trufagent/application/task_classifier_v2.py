from __future__ import annotations

from trufagent.domain.prepare_v2 import Complexity, PhaseEffort, PrepareEffort
from trufagent.domain.task import ModelTier, TaskKind, TaskSignals
from trufagent.domain.task_v2 import (
    SkillRecommendation,
    StructuralContext,
    TaskClassificationV2,
    TaskKindV2,
    TaskRisk,
    TaskScope,
    TaskSignalsV2,
    Uncertainty,
)

_COMPLEXITY_ORDER = {
    Complexity.LOW: 0,
    Complexity.MEDIUM: 1,
    Complexity.HIGH: 2,
}


def _max_complexity(*values: Complexity) -> Complexity:
    return max(values, key=_COMPLEXITY_ORDER.__getitem__)


def compact_v1_signals(signals: TaskSignals) -> TaskSignalsV2:
    """Compatibility adapter while natural-language extraction remains on v1."""

    kind = {
        TaskKind.SMALL_CHANGE: TaskKindV2.SMALL_CHANGE,
        TaskKind.BUG: TaskKindV2.FIX,
        TaskKind.FEATURE: TaskKindV2.FEATURE,
        TaskKind.ARCHITECTURE: TaskKindV2.ARCHITECTURE,
        TaskKind.DIAGNOSTIC: TaskKindV2.RESEARCH,
        TaskKind.VISUAL_REDESIGN: TaskKindV2.FEATURE,
        TaskKind.RESEARCH: TaskKindV2.RESEARCH,
        TaskKind.PLANNED_IMPLEMENTATION: TaskKindV2.FEATURE,
    }[signals.kind]

    if signals.open_decisions or kind in {TaskKindV2.ARCHITECTURE, TaskKindV2.RESEARCH}:
        uncertainty = Uncertainty.HIGH
    elif kind == TaskKindV2.FIX:
        uncertainty = (
            Uncertainty.HIGH
            if signals.cause_known is False
            else Uncertainty.LOW
            if signals.cause_known is True
            else Uncertainty.MEDIUM
        )
    elif kind == TaskKindV2.FEATURE:
        uncertainty = Uncertainty.LOW if signals.solution_known else Uncertainty.MEDIUM
    else:
        uncertainty = Uncertainty.LOW

    broad = signals.multi_surface or signals.shared_contract or signals.shared_symptom
    high_risk = any(
        (
            signals.persistence,
            signals.permissions,
            signals.secrets,
            signals.production,
            signals.shared_contract,
        )
    )
    if kind == TaskKindV2.ARCHITECTURE or signals.persistence or signals.shared_contract:
        structural_context = StructuralContext.REQUIRED
    elif broad or kind == TaskKindV2.RESEARCH:
        structural_context = StructuralContext.USEFUL
    else:
        structural_context = StructuralContext.NONE

    return TaskSignalsV2(
        kind=kind,
        uncertainty=uncertainty,
        scope=TaskScope.BROAD if broad else TaskScope.LOCAL,
        risk=TaskRisk.HIGH if high_risk else TaskRisk.NORMAL,
        open_decisions=signals.open_decisions,
        structural_context=structural_context,
    )


def classify_task_v2(signals: TaskSignalsV2) -> TaskClassificationV2:
    uncertainty = Complexity(signals.uncertainty.value)
    scope = Complexity.MEDIUM if signals.scope == TaskScope.BROAD else Complexity.LOW
    risk = Complexity.HIGH if signals.risk == TaskRisk.HIGH else Complexity.LOW
    kind = {
        TaskKindV2.SMALL_CHANGE: Complexity.LOW,
        TaskKindV2.FIX: Complexity.LOW,
        TaskKindV2.FEATURE: Complexity.MEDIUM,
        TaskKindV2.RESEARCH: Complexity.HIGH,
        TaskKindV2.ARCHITECTURE: Complexity.HIGH,
    }[signals.kind]
    complexity = _max_complexity(uncertainty, scope, risk, kind)
    model_tier = {
        Complexity.LOW: ModelTier.ECONOMY,
        Complexity.MEDIUM: ModelTier.BALANCED,
        Complexity.HIGH: ModelTier.FRONTIER,
    }[complexity]
    effort = {
        Complexity.LOW: PrepareEffort(
            explore=PhaseEffort.LOW,
            implement=PhaseEffort.LOW,
            verify=PhaseEffort.LOW,
        ),
        Complexity.MEDIUM: PrepareEffort(
            explore=PhaseEffort.MEDIUM,
            implement=PhaseEffort.MEDIUM,
            verify=PhaseEffort.MEDIUM,
        ),
        Complexity.HIGH: PrepareEffort(
            explore=PhaseEffort.HIGH,
            implement=PhaseEffort.MEDIUM,
            verify=PhaseEffort.HIGH,
        ),
    }[complexity]
    if signals.kind == TaskKindV2.RESEARCH:
        effort = effort.model_copy(update={"implement": PhaseEffort.NONE})

    skills: list[SkillRecommendation] = []
    reasons = [f"kind:{signals.kind.value}", f"uncertainty:{signals.uncertainty.value}"]
    if signals.kind == TaskKindV2.FIX and signals.uncertainty == Uncertainty.HIGH:
        skills.append(
            SkillRecommendation(
                name="systematic-debugging",
                reason="fix cause is not yet demonstrated",
            )
        )
        reasons.append("cause-not-established")
    if signals.kind in {TaskKindV2.FIX, TaskKindV2.FEATURE}:
        skills.extend(
            [
                SkillRecommendation(
                    name="implement-with-evidence",
                    reason="behavior change requires proportionate implementation proof",
                ),
                SkillRecommendation(
                    name="review-and-remember",
                    reason="completed change requires review and durable-memory triage",
                ),
            ]
        )
    if signals.open_decisions:
        skills.append(
            SkillRecommendation(
                name="brainstorming",
                reason="task contains open decisions",
            )
        )
        reasons.append("open-decisions")
    if signals.scope == TaskScope.BROAD:
        reasons.append("broad-scope")
    if signals.risk == TaskRisk.HIGH:
        reasons.append("high-risk")
    if signals.structural_context != StructuralContext.NONE:
        reasons.append(f"structural-context:{signals.structural_context.value}")

    return TaskClassificationV2(
        complexity=complexity,
        model_tier=model_tier,
        effort=effort,
        skills=skills,
        query_graph=signals.structural_context != StructuralContext.NONE,
        reasons=reasons,
    )
