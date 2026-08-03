from trufagent.application.model_routing import route_models
from trufagent.application.task_classifier import classify_task
from trufagent.domain.task import ModelTier, TaskKind, TaskSignals


def test_small_change_uses_economy_for_every_phase() -> None:
    route = route_models(classify_task(TaskSignals(kind=TaskKind.SMALL_CHANGE)))

    assert route.coordinator == ModelTier.ECONOMY
    assert route.exploration == ModelTier.ECONOMY
    assert route.execution == ModelTier.ECONOMY
    assert route.verification == ModelTier.ECONOMY


def test_secret_diagnostic_reserves_frontier_for_critical_verification() -> None:
    route = route_models(classify_task(TaskSignals(kind=TaskKind.DIAGNOSTIC, secrets=True)))

    assert route.coordinator == ModelTier.ECONOMY
    assert route.exploration == ModelTier.BALANCED
    assert route.execution == ModelTier.ECONOMY
    assert route.verification == ModelTier.FRONTIER


def test_research_can_route_to_no_execution_model() -> None:
    route = route_models(
        classify_task(TaskSignals(kind=TaskKind.RESEARCH, hypothesis_may_negate_work=True))
    )

    assert route.execution == ModelTier.NONE
