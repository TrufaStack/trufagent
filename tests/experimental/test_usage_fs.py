from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trufagent.experimental.delegation_domain import DelegationPhase, UsageRecord
from trufagent.experimental.usage_fs import JsonlUsageRepository
from trufagent.infrastructure.model_profiles import Harness


def _record(invocation_id: str) -> UsageRecord:
    return UsageRecord(
        schema="trufagent.usage.v1",
        invocation_id=invocation_id,
        session_id="ses_example",
        recorded_at=datetime(2026, 7, 31, tzinfo=UTC),
        phase=DelegationPhase.EXPLORATION,
        harness=Harness.CODEX,
        model="gpt-5.6-terra",
        input_tokens=100,
        output_tokens=10,
        cost_usd=Decimal("0.01"),
    )


def test_repository_appends_create_only_usage_events(tmp_path: Path) -> None:
    repository = JsonlUsageRepository(tmp_path)

    path = repository.append(_record("inv_001"))
    repository.append(_record("inv_002"))

    assert len(path.read_text().splitlines()) == 2
    assert len(repository.load("ses_example").records) == 2


def test_repository_rejects_duplicate_invocation_ids(tmp_path: Path) -> None:
    repository = JsonlUsageRepository(tmp_path)
    repository.append(_record("inv_001"))

    with pytest.raises(ValueError, match="duplicate"):
        repository.append(_record("inv_001"))

    assert len(repository.path_for("ses_example").read_text().splitlines()) == 1
