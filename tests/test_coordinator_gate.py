from trufagent.application.coordinator_gate import (
    CoordinatorDisposition,
    apply_coordinator_gate,
    evaluate_host_coordinator,
)
from trufagent.application.task_classifier import classify_task
from trufagent.domain.task import ModelRouting, ModelTier, TaskKind, TaskSignals


def test_embedded_host_owns_coordinator_without_second_model() -> None:
    strategy = classify_task(TaskSignals(kind=TaskKind.SMALL_CHANGE, solution_known=True))
    gate = evaluate_host_coordinator(strategy)
    route = ModelRouting(
        coordinator=ModelTier.ECONOMY,
        exploration=ModelTier.ECONOMY,
        execution=ModelTier.ECONOMY,
        verification=ModelTier.ECONOMY,
    )

    updated = apply_coordinator_gate(route, gate)

    assert gate.disposition == CoordinatorDisposition.HOST_OWNED
    assert gate.handoff.phase.value == "coordinator"
    assert updated.coordinator == ModelTier.NONE
