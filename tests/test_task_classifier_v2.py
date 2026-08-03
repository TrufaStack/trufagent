from __future__ import annotations

import pytest

from trufagent.application.model_routing import route_models
from trufagent.application.task_classifier import classify_task
from trufagent.application.task_classifier_v2 import classify_task_v2, compact_v1_signals
from trufagent.domain.prepare_v2 import Complexity, PhaseEffort
from trufagent.domain.task import ModelTier, TaskKind, TaskSignals
from trufagent.domain.task_v2 import (
    StructuralContext,
    TaskKindV2,
    TaskRisk,
    TaskScope,
    TaskSignalsV2,
    Uncertainty,
)


@pytest.mark.parametrize(
    ("signals", "complexity", "tier", "skills"),
    [
        (
            TaskSignalsV2(kind=TaskKindV2.SMALL_CHANGE, uncertainty=Uncertainty.LOW),
            Complexity.LOW,
            ModelTier.ECONOMY,
            [],
        ),
        (
            TaskSignalsV2(kind=TaskKindV2.FEATURE, uncertainty=Uncertainty.LOW),
            Complexity.MEDIUM,
            ModelTier.BALANCED,
            ["implement-with-evidence", "review-and-remember"],
        ),
        (
            TaskSignalsV2(kind=TaskKindV2.FIX, uncertainty=Uncertainty.HIGH),
            Complexity.HIGH,
            ModelTier.FRONTIER,
            [
                "systematic-debugging",
                "implement-with-evidence",
                "review-and-remember",
            ],
        ),
        (
            TaskSignalsV2(
                kind=TaskKindV2.ARCHITECTURE,
                uncertainty=Uncertainty.HIGH,
                open_decisions=True,
                structural_context=StructuralContext.REQUIRED,
            ),
            Complexity.HIGH,
            ModelTier.FRONTIER,
            ["brainstorming"],
        ),
        (
            TaskSignalsV2(
                kind=TaskKindV2.FEATURE,
                uncertainty=Uncertainty.LOW,
                scope=TaskScope.BROAD,
            ),
            Complexity.MEDIUM,
            ModelTier.BALANCED,
            ["implement-with-evidence", "review-and-remember"],
        ),
        (
            TaskSignalsV2(
                kind=TaskKindV2.FIX,
                uncertainty=Uncertainty.LOW,
                risk=TaskRisk.HIGH,
            ),
            Complexity.HIGH,
            ModelTier.FRONTIER,
            ["implement-with-evidence", "review-and-remember"],
        ),
    ],
)
def test_v2_classification_matrix(signals, complexity, tier, skills) -> None:
    result = classify_task_v2(signals)

    assert result.complexity == complexity
    assert result.model_tier == tier
    assert [skill.name for skill in result.skills] == skills


def test_research_uses_frontier_without_an_implementation_phase() -> None:
    result = classify_task_v2(
        TaskSignalsV2(kind=TaskKindV2.RESEARCH, uncertainty=Uncertainty.HIGH)
    )

    assert result.model_tier == ModelTier.FRONTIER
    assert result.effort.explore == PhaseEffort.HIGH
    assert result.effort.implement == PhaseEffort.NONE
    assert result.effort.verify == PhaseEffort.HIGH


def test_structural_context_controls_graph_usage_directly() -> None:
    none = classify_task_v2(
        TaskSignalsV2(kind=TaskKindV2.SMALL_CHANGE, uncertainty=Uncertainty.LOW)
    )
    required = classify_task_v2(
        TaskSignalsV2(
            kind=TaskKindV2.FIX,
            uncertainty=Uncertainty.MEDIUM,
            structural_context=StructuralContext.REQUIRED,
        )
    )

    assert none.query_graph is False
    assert required.query_graph is True


def test_v1_compatibility_adapter_collapses_many_flags_into_six_signals() -> None:
    compact = compact_v1_signals(
        TaskSignals(
            kind=TaskKind.BUG,
            cause_known=False,
            persistence=True,
            silent_failure=True,
            shared_contract=True,
            multi_surface=True,
        )
    )

    assert compact == TaskSignalsV2(
        kind=TaskKindV2.FIX,
        uncertainty=Uncertainty.HIGH,
        scope=TaskScope.BROAD,
        risk=TaskRisk.HIGH,
        open_decisions=False,
        structural_context=StructuralContext.REQUIRED,
    )
    assert len(TaskSignalsV2.model_fields) == 6


@pytest.mark.parametrize(
    "signals",
    [
        TaskSignals(kind=TaskKind.SMALL_CHANGE, solution_known=True, localized=True),
        TaskSignals(kind=TaskKind.BUG, cause_known=False),
        TaskSignals(kind=TaskKind.FEATURE, solution_known=True),
        TaskSignals(kind=TaskKind.ARCHITECTURE, open_decisions=True),
        TaskSignals(kind=TaskKind.RESEARCH),
    ],
)
def test_v2_preserves_the_core_v1_model_tier(signals: TaskSignals) -> None:
    v1_route = route_models(classify_task(signals))
    v1_tier = max(
        (v1_route.exploration, v1_route.execution, v1_route.verification),
        key={
            ModelTier.NONE: 0,
            ModelTier.ECONOMY: 1,
            ModelTier.BALANCED: 2,
            ModelTier.FRONTIER: 3,
        }.__getitem__,
    )
    v2 = classify_task_v2(compact_v1_signals(signals))

    assert v2.model_tier == v1_tier
