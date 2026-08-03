from decimal import Decimal
from pathlib import Path

import pytest

from trufagent.application.delegation import compile_delegation_protocol
from trufagent.domain.delegation import (
    ActionScope,
    DelegationPhase,
    HandoffStatus,
    PhaseHandoff,
    UsageLedger,
    UsageRecord,
)
from trufagent.domain.task import ModelRouting, ModelTier
from trufagent.infrastructure.model_profiles import Harness


def test_protocol_is_serial_and_only_execution_can_write(tmp_path: Path) -> None:
    protocol = compile_delegation_protocol(
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
        budget_limit_usd=Decimal("0.50"),
    )

    assert protocol.max_parallel == 1
    assert [step.model for step in protocol.steps] == [
        "gpt-5.6-luna",
        "gpt-5.6-sol",
        "gpt-5.6-luna",
        "gpt-5.6-sol",
    ]
    assert [
        step.phase for step in protocol.steps if step.action_scope == ActionScope.WORKTREE_WRITE
    ] == [DelegationPhase.EXECUTION]
    assert protocol.steps[-1].required_evidence == ("regression-test",)


def test_none_execution_is_an_explicit_skip(tmp_path: Path) -> None:
    protocol = compile_delegation_protocol(
        session_id="ses_example",
        project_root=tmp_path,
        harness=Harness.CLAUDE,
        route=ModelRouting(
            coordinator=ModelTier.ECONOMY,
            exploration=ModelTier.BALANCED,
            execution=ModelTier.NONE,
            verification=ModelTier.ECONOMY,
        ),
        evidence_required=[],
    )

    execution = protocol.steps[2]
    assert execution.model is None
    assert execution.action_scope == ActionScope.NONE
    assert execution.max_attempts == 0


def test_handoff_rejects_more_than_twelve_inspected_files() -> None:
    with pytest.raises(ValueError):
        PhaseHandoff(
            phase=DelegationPhase.EXPLORATION,
            status=HandoffStatus.WARNING,
            summary="Scope exhausted.",
            inspected_files=tuple(f"file-{index}.ts" for index in range(13)),
        )


def test_ledger_is_immutable_and_checks_budget(sample_usage_record) -> None:
    ledger = UsageLedger(
        session_id="ses_example",
        budget_limit_usd=Decimal("0.10"),
    )
    updated = ledger.add(sample_usage_record)

    assert ledger.records == ()
    assert updated.records == (sample_usage_record,)
    assert updated.known_cost_usd == Decimal("0.04")
    updated.authorize(Decimal("0.06"))
    with pytest.raises(ValueError, match="exceed"):
        updated.authorize(Decimal("0.061"))
    with pytest.raises(ValueError, match="duplicate"):
        updated.add(sample_usage_record)


def test_ledger_reserves_estimates_without_claiming_actual_cost() -> None:
    from datetime import UTC, datetime

    estimated = UsageRecord(
        schema="trufagent.usage.v1",
        invocation_id="inv_estimated",
        session_id="ses_example",
        recorded_at=datetime(2026, 8, 3, tzinfo=UTC),
        phase=DelegationPhase.EXPLORATION,
        harness=Harness.CODEX,
        model="gpt-5.6-sol",
        authorized_estimate_usd=Decimal("0.06"),
    )
    ledger = UsageLedger(
        session_id="ses_example",
        budget_limit_usd=Decimal("0.10"),
        records=(estimated,),
    )

    assert ledger.known_cost_usd == Decimal("0")
    assert ledger.reserved_cost_usd == Decimal("0.06")
    assert ledger.has_unknown_cost is True
    assert ledger.has_unbounded_unknown_cost is False
    assert ledger.cost_status == "estimated"
    ledger.authorize(Decimal("0.04"))
    with pytest.raises(ValueError, match="exceed"):
        ledger.authorize(Decimal("0.041"))


@pytest.fixture
def sample_usage_record() -> UsageRecord:
    from datetime import UTC, datetime

    return UsageRecord(
        schema="trufagent.usage.v1",
        invocation_id="inv_001",
        session_id="ses_example",
        recorded_at=datetime(2026, 7, 31, tzinfo=UTC),
        phase=DelegationPhase.EXPLORATION,
        harness=Harness.CODEX,
        model="gpt-5.6-terra",
        input_tokens=100,
        cached_input_tokens=80,
        output_tokens=20,
        cost_usd=Decimal("0.04"),
    )
