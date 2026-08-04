import json
from datetime import UTC, datetime

import pytest

from trufagent.cli import main
from trufagent.experimental.attempt import AttemptEvent, AttemptStatus, FailureKind
from trufagent.experimental.attempt_fs import (
    AttemptLedgerError,
    JsonlAttemptRepository,
)
from trufagent.experimental.delegation_domain import DelegationPhase


def _event(event_id: str, status: AttemptStatus, **updates) -> AttemptEvent:
    data = {
        "schema": "trufagent.attempt.v1",
        "event_id": event_id,
        "attempt_id": "att_1",
        "session_id": "ses_1",
        "task_digest": "a" * 64,
        "phase": DelegationPhase.EXPLORATION,
        "attempt": 1,
        "status": status,
        "created_at": datetime(2026, 7, 31, tzinfo=UTC),
        **updates,
    }
    return AttemptEvent.model_validate(data)


def test_repository_requires_started_before_terminal(tmp_path) -> None:
    repository = JsonlAttemptRepository(tmp_path)

    with pytest.raises(AttemptLedgerError, match="requires exactly one started"):
        repository.append(
            _event(
                "evt_failed",
                AttemptStatus.FAILED,
                failure_kind=FailureKind.TRANSIENT_PROCESS,
                worktree_unchanged=True,
            )
        )


def test_repository_preserves_create_only_attempt_history(tmp_path) -> None:
    repository = JsonlAttemptRepository(tmp_path)
    repository.append(_event("evt_started", AttemptStatus.STARTED))
    repository.append(
        _event(
            "evt_failed",
            AttemptStatus.FAILED,
            failure_kind=FailureKind.TRANSIENT_PROCESS,
            worktree_unchanged=True,
        )
    )

    events = repository.for_task("ses_1", "a" * 64)
    assert [event.status for event in events] == [
        AttemptStatus.STARTED,
        AttemptStatus.FAILED,
    ]
    with pytest.raises(AttemptLedgerError, match="duplicate attempt event"):
        repository.append(_event("evt_started", AttemptStatus.STARTED))


def test_cli_exposes_safe_attempt_history(tmp_path, capsys) -> None:
    JsonlAttemptRepository(tmp_path).append(_event("evt_started", AttemptStatus.STARTED))

    assert main(["delegation", "attempts", str(tmp_path), "ses_1"]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["schema"] == "trufagent.attempt-history.v1"
    assert output["events"][0]["task_digest"] == "a" * 64
    assert "prompt" not in output["events"][0]
