from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from trufagent.experimental.attempt import AttemptEvent, AttemptStatus


class AttemptLedgerError(RuntimeError):
    pass


class JsonlAttemptRepository:
    def __init__(self, project_root: Path) -> None:
        self.root = Path(project_root) / ".trufagent" / "state" / "attempts"

    def path_for(self, session_id: str) -> Path:
        return self.root / f"{session_id}.jsonl"

    def load(self, session_id: str) -> tuple[AttemptEvent, ...]:
        path = self.path_for(session_id)
        if not path.is_file():
            return ()
        try:
            events = tuple(
                AttemptEvent.model_validate_json(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        except (OSError, ValidationError, json.JSONDecodeError) as exc:
            raise AttemptLedgerError(f"invalid attempt ledger: {path}") from exc
        ids = [event.event_id for event in events]
        if len(ids) != len(set(ids)):
            raise AttemptLedgerError(f"duplicate attempt event in ledger: {path}")
        return events

    def append(self, event: AttemptEvent) -> Path:
        path = self.path_for(event.session_id)
        events = self.load(event.session_id)
        if any(item.event_id == event.event_id for item in events):
            raise AttemptLedgerError(f"duplicate attempt event: {event.event_id}")
        matching = [item for item in events if item.attempt_id == event.attempt_id]
        if event.status == AttemptStatus.STARTED:
            if matching:
                raise AttemptLedgerError(f"attempt already started: {event.attempt_id}")
        else:
            if len(matching) != 1 or matching[0].status != AttemptStatus.STARTED:
                raise AttemptLedgerError("terminal event requires exactly one started event")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(event.model_dump_json(by_alias=True) + "\n")
        return path

    def for_task(self, session_id: str, task_digest: str) -> tuple[AttemptEvent, ...]:
        return tuple(event for event in self.load(session_id) if event.task_digest == task_digest)
