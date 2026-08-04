from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from trufagent.domain.task import Harness, ModelRouting, ModelTier
from trufagent.experimental.delegation_domain import (
    ActionScope,
    DelegationPhase,
    DelegationProtocol,
    DelegationStep,
)
from trufagent.infrastructure.model_profiles import (
    load_model_overrides,
    resolve_model,
)


class CompileDelegationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    harness: Harness
    model_route: ModelRouting
    evidence_required: list[str] = Field(default_factory=list)
    budget_limit_usd: Decimal | None = Field(default=None, ge=0)


_PHASE_SCOPE = {
    DelegationPhase.COORDINATOR: ActionScope.READ_ONLY,
    DelegationPhase.EXPLORATION: ActionScope.READ_ONLY,
    DelegationPhase.EXECUTION: ActionScope.WORKTREE_WRITE,
    DelegationPhase.VERIFICATION: ActionScope.READ_ONLY,
}


def compile_request(
    project_root: Path,
    request: CompileDelegationRequest,
) -> DelegationProtocol:
    return compile_delegation_protocol(
        session_id=request.session_id,
        project_root=project_root,
        harness=request.harness,
        route=request.model_route,
        evidence_required=request.evidence_required,
        budget_limit_usd=request.budget_limit_usd,
    )


def compile_delegation_protocol(
    *,
    session_id: str,
    project_root: Path,
    harness: Harness,
    route: ModelRouting,
    evidence_required: list[str],
    budget_limit_usd: Decimal | None = None,
) -> DelegationProtocol:
    overrides = load_model_overrides(project_root)
    steps: list[DelegationStep] = []
    for phase in DelegationPhase:
        tier = ModelTier(getattr(route, phase.value))
        skipped = tier == ModelTier.NONE
        steps.append(
            DelegationStep(
                phase=phase,
                tier=tier,
                model=resolve_model(harness, tier, overrides),
                action_scope=ActionScope.NONE if skipped else _PHASE_SCOPE[phase],
                max_attempts=0 if skipped else 1,
                required_evidence=(
                    tuple(evidence_required) if phase == DelegationPhase.VERIFICATION else ()
                ),
            )
        )
    return DelegationProtocol(
        schema="trufagent.delegation.v1",
        session_id=session_id,
        harness=harness,
        budget_limit_usd=budget_limit_usd,
        steps=tuple(steps),
    )
