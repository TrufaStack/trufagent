from pathlib import Path

import pytest

from trufagent.experimental.pilot_fs import (
    PilotLedgerError,
    PilotTaskKind,
    PilotTaskStatus,
    begin_pilot_task,
    completed_pilot_task_count,
    finish_pilot_task,
    load_pilot_ledger,
)
from trufagent.experimental.promotion_fs import initialize_pilot_policy, load_promotion_policy
from trufagent.experimental.promotion_workspace import prepare_promotion_workspace


def _ready_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("VALUE = 1\n")
    initialize_pilot_policy(source)
    policy = load_promotion_policy(source)
    prepare_promotion_workspace(source, policy, workspace_base=tmp_path / "workspaces")
    return source


def test_pilot_task_is_fingerprint_sealed_and_counted_once(tmp_path: Path) -> None:
    source = _ready_source(tmp_path)

    begin_pilot_task(source, "task-001", PilotTaskKind.SMALL_CHANGE)
    finished = finish_pilot_task(source, "task-001", PilotTaskStatus.PASSED)

    assert finished.status == PilotTaskStatus.PASSED
    assert finished.source_unchanged is True
    assert finished.external_service_calls == 0
    assert completed_pilot_task_count(source) == 1
    assert len(load_pilot_ledger(source)) == 2


def test_pilot_task_fails_if_protected_source_changes(tmp_path: Path) -> None:
    source = _ready_source(tmp_path)
    begin_pilot_task(source, "task-002", PilotTaskKind.AMBIGUOUS_BUG)
    (source / "app.py").write_text("VALUE = 2\n")

    finished = finish_pilot_task(source, "task-002", PilotTaskStatus.PASSED)

    assert finished.status == PilotTaskStatus.FAILED
    assert finished.source_unchanged is False
    assert completed_pilot_task_count(source) == 0


def test_pilot_task_ids_cannot_be_reused(tmp_path: Path) -> None:
    source = _ready_source(tmp_path)
    begin_pilot_task(source, "task-003", PilotTaskKind.FEATURE)

    with pytest.raises(PilotLedgerError, match="already exists"):
        begin_pilot_task(source, "task-003", PilotTaskKind.FEATURE)
