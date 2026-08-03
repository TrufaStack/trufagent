from __future__ import annotations

from trufagent.application.prepare_task import PreparedTask
from trufagent.domain.prepare_v2 import (
    Complexity,
    PhaseEffort,
    PrepareContext,
    PrepareEffort,
    PrepareGraphReference,
    PrepareMemoryReference,
    PrepareQuestion,
    PrepareSkill,
    PrepareStatus,
    PrepareTaskSummary,
    PrepareV2Result,
)
from trufagent.domain.task import EffortLevel, Level, ModelTier, RiskLevel

_COMPLEXITY_ORDER = {
    Complexity.LOW: 0,
    Complexity.MEDIUM: 1,
    Complexity.HIGH: 2,
}

_MODEL_ORDER = {
    ModelTier.NONE: 0,
    ModelTier.ECONOMY: 1,
    ModelTier.BALANCED: 2,
    ModelTier.FRONTIER: 3,
}


def _max_complexity(*values: Complexity) -> Complexity:
    return max(values, key=_COMPLEXITY_ORDER.__getitem__)


def _complexity(prepared: PreparedTask) -> Complexity:
    if prepared.plan is None:
        raise ValueError("a ready prepared task must include a plan")
    profile = prepared.plan.strategy.task_profile
    ambiguity = {
        Level.LOW: Complexity.LOW,
        Level.MEDIUM: Complexity.MEDIUM,
        Level.HIGH: Complexity.HIGH,
    }[profile.ambiguity]
    risk = {
        RiskLevel.LOW: Complexity.LOW,
        RiskLevel.MEDIUM: Complexity.MEDIUM,
        RiskLevel.HIGH: Complexity.HIGH,
        RiskLevel.CRITICAL: Complexity.HIGH,
    }[profile.risk]
    return _max_complexity(ambiguity, risk)


def _effort(value: EffortLevel) -> PhaseEffort:
    if value == EffortLevel.CRITICAL:
        return PhaseEffort.HIGH
    return PhaseEffort(value.value)


def _model_tier(prepared: PreparedTask) -> ModelTier:
    if prepared.plan is None:
        raise ValueError("a ready prepared task must include a plan")
    route = prepared.plan.model_route
    return max(
        (route.exploration, route.execution, route.verification),
        key=_MODEL_ORDER.__getitem__,
    )


def _skill_reason(name: str, reasons: list[str]) -> str:
    if name == "systematic-debugging" and "unknown-cause" in reasons:
        return "bug cause is not yet demonstrated"
    if name == "brainstorming" and "open-decisions" in reasons:
        return "task contains open decisions"
    return "selected by task strategy or user override"


def project_prepare_v2(prepared: PreparedTask) -> PrepareV2Result:
    """Project the current planner into the compact v2 contract.

    This is a compatibility boundary: v1 remains authoritative while the v2
    vertical slice is introduced and tested.
    """

    extraction = prepared.extraction
    if not extraction.ready_to_plan:
        return PrepareV2Result(
            status=PrepareStatus.NEEDS_INPUT,
            questions=[
                PrepareQuestion(field=question.field, prompt=question.prompt)
                for question in extraction.questions
            ],
            reasons=list(extraction.strategy.reasons),
        )
    if prepared.plan is None:
        raise ValueError("ready extraction did not include a task plan")

    plan = prepared.plan
    context = plan.context
    reasons = list(plan.strategy.reasons)
    return PrepareV2Result(
        status=PrepareStatus.READY,
        task=PrepareTaskSummary(
            kind=extraction.signals.kind,
            complexity=_complexity(prepared),
        ),
        model_tier=_model_tier(prepared),
        effort=PrepareEffort(
            explore=_effort(plan.strategy.budgets.exploration),
            implement=_effort(plan.strategy.budgets.execution),
            verify=_effort(plan.strategy.budgets.verification),
        ),
        skills=[
            PrepareSkill(
                name=skill.name,
                reason=_skill_reason(skill.name, reasons),
                location=skill.locations[0] if skill.locations else None,
            )
            for skill in plan.selected_skills
        ],
        context=PrepareContext(
            memories=[
                PrepareMemoryReference(
                    memory_id=item.memory_id,
                    title=item.title,
                    kind=item.kind.value,
                    estimated_tokens=item.estimated_tokens,
                )
                for item in context.items
            ],
            graph=[
                PrepareGraphReference(label=node.label, source_file=node.source_file)
                for node in (context.cartography.nodes if context.cartography else [])
            ],
            estimated_tokens=context.estimated_tokens,
            omitted_count=context.omitted_count,
        ),
        warnings=list(dict.fromkeys(context.warnings + plan.warnings)),
        reasons=reasons,
    )
