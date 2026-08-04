from pathlib import Path

import pytest

from trufagent.application.errors import SafeAdapterError
from trufagent.domain.task import Harness, ModelRouting, ModelTier
from trufagent.experimental.delegation import compile_delegation_protocol
from trufagent.experimental.delegation_domain import (
    DelegationPhase,
    HandoffStatus,
    PhaseHandoff,
)
from trufagent.experimental.delegation_executor import execute_dry_run
from trufagent.experimental.fake_phase_adapter import ScriptedPhaseAdapter


def _protocol(tmp_path: Path):
    return compile_delegation_protocol(
        session_id="ses_example",
        project_root=tmp_path,
        harness=Harness.CODEX,
        route=ModelRouting(
            coordinator=ModelTier.ECONOMY,
            exploration=ModelTier.BALANCED,
            execution=ModelTier.ECONOMY,
            verification=ModelTier.FRONTIER,
        ),
        evidence_required=["regression-test"],
    )


def _successes() -> dict[DelegationPhase, PhaseHandoff]:
    return {
        DelegationPhase.COORDINATOR: PhaseHandoff(
            phase=DelegationPhase.COORDINATOR,
            status=HandoffStatus.SUCCESS,
            summary="Scope accepted.",
        ),
        DelegationPhase.EXPLORATION: PhaseHandoff(
            phase=DelegationPhase.EXPLORATION,
            status=HandoffStatus.SUCCESS,
            summary="Cause confirmed.",
            artifacts=("notes/exploration.json",),
        ),
        DelegationPhase.EXECUTION: PhaseHandoff(
            phase=DelegationPhase.EXECUTION,
            status=HandoffStatus.SUCCESS,
            summary="Change applied.",
            worktree_changed=True,
        ),
        DelegationPhase.VERIFICATION: PhaseHandoff(
            phase=DelegationPhase.VERIFICATION,
            status=HandoffStatus.SUCCESS,
            summary="Regression test passed.",
            evidence=("regression-test",),
        ),
    }


def test_dry_run_completes_once_per_phase(tmp_path: Path) -> None:
    adapter = ScriptedPhaseAdapter(_successes())

    report = execute_dry_run(_protocol(tmp_path), adapter)

    assert report.status == HandoffStatus.SUCCESS
    assert adapter.invocations == list(DelegationPhase)
    assert report.artifacts == ("notes/exploration.json",)


def test_warning_returns_control_without_running_later_phases(tmp_path: Path) -> None:
    handoffs = _successes()
    handoffs[DelegationPhase.EXPLORATION] = PhaseHandoff(
        phase=DelegationPhase.EXPLORATION,
        status=HandoffStatus.WARNING,
        summary="Cause remains ambiguous.",
        next_actions=("Ask the coordinator to refine scope.",),
    )
    adapter = ScriptedPhaseAdapter(handoffs)

    report = execute_dry_run(_protocol(tmp_path), adapter)

    assert report.status == HandoffStatus.WARNING
    assert report.stopped_at == DelegationPhase.EXPLORATION
    assert adapter.invocations == [
        DelegationPhase.COORDINATOR,
        DelegationPhase.EXPLORATION,
    ]


def test_read_only_phase_cannot_claim_a_worktree_change(tmp_path: Path) -> None:
    handoffs = _successes()
    handoffs[DelegationPhase.EXPLORATION] = handoffs[DelegationPhase.EXPLORATION].model_copy(
        update={"worktree_changed": True}
    )
    adapter = ScriptedPhaseAdapter(handoffs)

    report = execute_dry_run(_protocol(tmp_path), adapter)

    assert report.status == HandoffStatus.ERROR
    assert "outside execution" in report.summary
    assert adapter.invocations == [
        DelegationPhase.COORDINATOR,
        DelegationPhase.EXPLORATION,
    ]


def test_verification_must_supply_every_required_evidence(tmp_path: Path) -> None:
    handoffs = _successes()
    handoffs[DelegationPhase.VERIFICATION] = handoffs[DelegationPhase.VERIFICATION].model_copy(
        update={"evidence": ()}
    )
    adapter = ScriptedPhaseAdapter(handoffs)

    report = execute_dry_run(_protocol(tmp_path), adapter)

    assert report.status == HandoffStatus.ERROR
    assert "missing required evidence" in report.summary
    assert adapter.invocations.count(DelegationPhase.VERIFICATION) == 1


def test_error_handoff_requires_explicit_recovery_contract() -> None:
    with pytest.raises(ValueError, match="recovery"):
        PhaseHandoff(
            phase=DelegationPhase.EXPLORATION,
            status=HandoffStatus.ERROR,
            summary="Tool failed.",
        )


def test_adapter_exception_is_normalized_without_retry(tmp_path: Path) -> None:
    class BrokenAdapter:
        calls = 0

        def invoke(self, step, previous):
            del step, previous
            self.calls += 1
            raise RuntimeError("possibly sensitive provider detail")

    adapter = BrokenAdapter()

    report = execute_dry_run(_protocol(tmp_path), adapter)

    assert report.status == HandoffStatus.ERROR
    assert report.stopped_at == DelegationPhase.COORDINATOR
    assert "RuntimeError" in report.summary
    assert "sensitive" not in report.summary
    assert adapter.calls == 1


def test_closed_adapter_diagnostic_code_is_safe_to_surface(tmp_path: Path) -> None:
    class SafeFailure(SafeAdapterError):
        diagnostic_code = "handoff-schema-invalid"

    class BrokenAdapter:
        def invoke(self, step, previous):
            del step, previous
            raise SafeFailure("SECRET=must-not-surface")

    report = execute_dry_run(_protocol(tmp_path), BrokenAdapter())

    assert "handoff-schema-invalid" in report.summary
    assert "SECRET" not in report.summary
