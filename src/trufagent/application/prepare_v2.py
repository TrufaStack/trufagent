from __future__ import annotations

from trufagent.application.prepare_task import PreparedTask
from trufagent.application.task_classifier_v2 import classify_task_v2, compact_v1_signals
from trufagent.domain.prepare_v2 import (
    PrepareContext,
    PrepareGraphReference,
    PrepareMemoryReference,
    PrepareQuestion,
    PrepareSkill,
    PrepareStatus,
    PrepareTaskSummary,
    PrepareV2Result,
    SkillPhase,
)


def project_prepare_v2(
    prepared: PreparedTask,
    *,
    harness: str | None = None,
) -> PrepareV2Result:
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
    signals_v2 = compact_v1_signals(extraction.signals)
    classification = classify_task_v2(signals_v2)
    selected = {skill.name: skill for skill in plan.selected_skills}
    recommended_locations = {name: skill.location_for(harness) for name, skill in selected.items()}
    skills = [
        PrepareSkill(
            name=recommendation.name,
            reason=recommendation.reason,
            phase=recommendation.phase,
            location=(
                recommended_locations[recommendation.name].path
                if recommendation.name in recommended_locations
                and recommended_locations[recommendation.name] is not None
                else None
            ),
            platform=(
                recommended_locations[recommendation.name].platform
                if recommendation.name in recommended_locations
                and recommended_locations[recommendation.name] is not None
                else None
            ),
        )
        for recommendation in classification.skills
        if recommendation.name in selected
    ]
    recommended_names = {skill.name for skill in skills}
    skills.extend(
        PrepareSkill(
            name=skill.name,
            reason="selected by user override",
            phase=SkillPhase.ANY,
            location=(location.path if (location := skill.location_for(harness)) else None),
            platform=location.platform if location else None,
        )
        for skill in plan.selected_skills
        if skill.name not in recommended_names
    )
    return PrepareV2Result(
        status=PrepareStatus.READY,
        task=PrepareTaskSummary(
            kind=signals_v2.kind.value,
            complexity=classification.complexity,
        ),
        model_tier=classification.model_tier,
        effort=classification.effort,
        skills=skills,
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
        reasons=classification.reasons,
    )
