from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from trufagent.experimental.promotion_workspace import operation_gate_is_enforced
from trufagent.infrastructure.worktree_fingerprint import fingerprint_worktree


class PilotLedgerError(RuntimeError):
    pass


class PilotTaskKind(StrEnum):
    SMALL_CHANGE = "small-change"
    AMBIGUOUS_BUG = "ambiguous-bug"
    FEATURE = "feature"
    ARCHITECTURE = "architecture"
    MEMORY = "memory"


class PilotTaskStatus(StrEnum):
    STARTED = "started"
    PASSED = "passed"
    FAILED = "failed"


class PilotTaskRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.pilot-task\.v1$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,63}$")
    kind: PilotTaskKind
    status: PilotTaskStatus
    started_at: datetime
    finished_at: datetime | None = None
    source_fingerprint_before: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_fingerprint_after: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_unchanged: bool | None = None
    operation_gate_enforced: bool
    external_service_calls: int = Field(default=0, ge=0, le=0)


def _ledger_path(project_root: Path) -> Path:
    return Path(project_root).resolve() / ".trufagent" / "state" / "pilot-tasks.jsonl"


def load_pilot_ledger(project_root: Path) -> tuple[PilotTaskRecord, ...]:
    path = _ledger_path(project_root)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return ()
    try:
        return tuple(PilotTaskRecord.model_validate_json(line) for line in lines if line.strip())
    except ValueError as exc:
        raise PilotLedgerError("invalid pilot task ledger") from exc


def _append(project_root: Path, record: PilotTaskRecord) -> None:
    path = _ledger_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(record.model_dump_json(by_alias=True) + "\n")


def begin_pilot_task(
    project_root: Path,
    task_id: str,
    kind: PilotTaskKind,
) -> PilotTaskRecord:
    records = load_pilot_ledger(project_root)
    if any(record.task_id == task_id for record in records):
        raise PilotLedgerError("pilot task id already exists")
    if not operation_gate_is_enforced(project_root):
        raise PilotLedgerError("operation gate must be enforced before pilot work")
    record = PilotTaskRecord(
        schema="trufagent.pilot-task.v1",
        task_id=task_id,
        kind=kind,
        status=PilotTaskStatus.STARTED,
        started_at=datetime.now(UTC),
        source_fingerprint_before=fingerprint_worktree(project_root),
        operation_gate_enforced=True,
    )
    _append(project_root, record)
    return record


def finish_pilot_task(
    project_root: Path,
    task_id: str,
    status: PilotTaskStatus,
) -> PilotTaskRecord:
    if status == PilotTaskStatus.STARTED:
        raise PilotLedgerError("terminal pilot status is required")
    records = load_pilot_ledger(project_root)
    matches = [record for record in records if record.task_id == task_id]
    if len(matches) != 1 or matches[0].status != PilotTaskStatus.STARTED:
        raise PilotLedgerError("pilot task is missing or already finished")
    started = matches[0]
    after = fingerprint_worktree(project_root)
    unchanged = after == started.source_fingerprint_before
    effective_status = status if unchanged else PilotTaskStatus.FAILED
    record = started.model_copy(
        update={
            "status": effective_status,
            "finished_at": datetime.now(UTC),
            "source_fingerprint_after": after,
            "source_unchanged": unchanged,
            "operation_gate_enforced": operation_gate_is_enforced(project_root),
        }
    )
    _append(project_root, record)
    return record


def completed_pilot_task_count(project_root: Path) -> int:
    return sum(
        record.status == PilotTaskStatus.PASSED
        and record.source_unchanged is True
        and record.operation_gate_enforced
        and record.external_service_calls == 0
        for record in load_pilot_ledger(project_root)
    )
