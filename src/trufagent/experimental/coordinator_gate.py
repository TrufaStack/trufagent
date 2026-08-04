from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from trufagent.domain.task import ModelRouting, ModelTier, TaskStrategy
from trufagent.experimental.delegation_domain import DelegationPhase, HandoffStatus, PhaseHandoff


class CoordinatorDisposition(StrEnum):
    HOST_OWNED = "host-owned"


class CoordinatorGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: HandoffStatus
    summary: str
    next_actions: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    disposition: CoordinatorDisposition
    handoff: PhaseHandoff


def evaluate_host_coordinator(strategy: TaskStrategy) -> CoordinatorGateResult:
    handoff = PhaseHandoff(
        phase=DelegationPhase.COORDINATOR,
        status=HandoffStatus.SUCCESS,
        summary=(
            "Host accepted the deterministic runtime strategy with "
            f"autonomy={strategy.autonomy_boundary.value}."
        ),
        next_actions=("Do not invoke a second coordinator model.",),
    )
    return CoordinatorGateResult(
        status=HandoffStatus.SUCCESS,
        summary="Coordinator phase is already owned by the host agent.",
        next_actions=("Compile coordinator with tier none.",),
        disposition=CoordinatorDisposition.HOST_OWNED,
        handoff=handoff,
    )


def apply_coordinator_gate(
    route: ModelRouting,
    gate: CoordinatorGateResult,
) -> ModelRouting:
    del gate
    return route.model_copy(update={"coordinator": ModelTier.NONE})
