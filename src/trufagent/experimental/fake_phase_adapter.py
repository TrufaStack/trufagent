from __future__ import annotations

from trufagent.experimental.delegation_domain import (
    DelegationPhase,
    DelegationStep,
    PhaseHandoff,
)


class ScriptedPhaseAdapter:
    """Deterministic adapter for harness tests; it never invokes a model."""

    def __init__(self, handoffs: dict[DelegationPhase, PhaseHandoff]) -> None:
        self.handoffs = handoffs
        self.invocations: list[DelegationPhase] = []

    def invoke(
        self,
        step: DelegationStep,
        previous: tuple[PhaseHandoff, ...],
    ) -> PhaseHandoff:
        del previous
        self.invocations.append(step.phase)
        if self.invocations.count(step.phase) > step.max_attempts:
            raise RuntimeError(f"attempt limit exceeded for {step.phase.value}")
        return self.handoffs[step.phase]
