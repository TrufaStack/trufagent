from __future__ import annotations

from typing import Protocol

from trufagent.application.errors import SafeAdapterError
from trufagent.domain.delegation import (
    ActionScope,
    DelegationProtocol,
    DelegationRunReport,
    DelegationStep,
    HandoffStatus,
    PhaseHandoff,
)


class PhaseAdapter(Protocol):
    def invoke(
        self,
        step: DelegationStep,
        previous: tuple[PhaseHandoff, ...],
    ) -> PhaseHandoff: ...


def _gate(step: DelegationStep, handoff: PhaseHandoff) -> str | None:
    if handoff.phase != step.phase:
        return f"adapter returned {handoff.phase.value} for {step.phase.value}"
    if handoff.status == HandoffStatus.SKIPPED:
        return "an invokable phase cannot return skipped"
    if step.action_scope != ActionScope.WORKTREE_WRITE and handoff.worktree_changed:
        return f"{step.phase.value} changed the worktree outside execution"
    missing = set(step.required_evidence) - set(handoff.evidence)
    if missing:
        return f"missing required evidence: {', '.join(sorted(missing))}"
    return None


def _gate_error(
    step: DelegationStep,
    handoffs: list[PhaseHandoff],
    reason: str,
) -> DelegationRunReport:
    return DelegationRunReport(
        status=HandoffStatus.ERROR,
        summary=f"Delegation stopped at {step.phase.value}: {reason}",
        next_actions=("Return control to the coordinator; do not retry automatically.",),
        artifacts=tuple(artifact for handoff in handoffs for artifact in handoff.artifacts),
        handoffs=tuple(handoffs),
        stopped_at=step.phase,
    )


def execute_dry_run(
    protocol: DelegationProtocol,
    adapter: PhaseAdapter,
) -> DelegationRunReport:
    handoffs: list[PhaseHandoff] = []
    for step in protocol.steps:
        if step.action_scope == ActionScope.NONE:
            handoffs.append(
                PhaseHandoff(
                    phase=step.phase,
                    status=HandoffStatus.SKIPPED,
                    summary=f"{step.phase.value} skipped by model route",
                )
            )
            continue
        try:
            handoff = adapter.invoke(step, tuple(handoffs))
        except Exception as exc:  # adapter boundary: normalize unexpected failures
            detail = f"adapter failure: {type(exc).__name__}"
            if isinstance(exc, SafeAdapterError):
                detail += f" ({exc.diagnostic_code})"
            return _gate_error(step, handoffs, detail)
        reason = _gate(step, handoff)
        if reason is not None:
            return _gate_error(step, handoffs, reason)
        handoffs.append(handoff)
        if handoff.status == HandoffStatus.ERROR:
            return DelegationRunReport(
                status=HandoffStatus.ERROR,
                summary=f"Delegation stopped at {step.phase.value}: {handoff.summary}",
                next_actions=(handoff.safe_retry or "Return control to the coordinator.",),
                artifacts=tuple(artifact for item in handoffs for artifact in item.artifacts),
                handoffs=tuple(handoffs),
                stopped_at=step.phase,
            )
        if handoff.status == HandoffStatus.WARNING:
            return DelegationRunReport(
                status=HandoffStatus.WARNING,
                summary=f"Coordinator review required after {step.phase.value}",
                next_actions=handoff.next_actions or ("Review the warning before continuing.",),
                artifacts=tuple(artifact for item in handoffs for artifact in item.artifacts),
                handoffs=tuple(handoffs),
                stopped_at=step.phase,
            )
    return DelegationRunReport(
        status=HandoffStatus.SUCCESS,
        summary="All delegation phases passed their acceptance gates.",
        next_actions=("Return the verified result to the coordinator.",),
        artifacts=tuple(artifact for handoff in handoffs for artifact in handoff.artifacts),
        handoffs=tuple(handoffs),
    )
