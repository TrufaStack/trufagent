from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from trufagent.experimental.delegation_domain import UsageLedger, UsageRecord


class UsageLedgerError(RuntimeError):
    pass


class JsonlUsageRepository:
    """Append-only per-session usage events without prompts or response content."""

    def __init__(self, project_root: Path) -> None:
        self.root = Path(project_root) / ".trufagent" / "state" / "usage"

    def path_for(self, session_id: str) -> Path:
        return self.root / f"{session_id}.jsonl"

    def load(
        self,
        session_id: str,
        *,
        budget_limit_usd=None,
    ) -> UsageLedger:
        path = self.path_for(session_id)
        records: tuple[UsageRecord, ...] = ()
        if path.is_file():
            try:
                records = tuple(
                    UsageRecord.model_validate_json(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
            except (OSError, ValidationError, json.JSONDecodeError) as exc:
                raise UsageLedgerError(f"invalid usage ledger: {path}") from exc
        ledger = UsageLedger(
            session_id=session_id,
            budget_limit_usd=budget_limit_usd,
        )
        for record in records:
            ledger = ledger.add(record)
        return ledger

    def append(self, record: UsageRecord) -> Path:
        path = self.path_for(record.session_id)
        ledger = self.load(record.session_id)
        ledger.add(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(record.model_dump_json(by_alias=True) + "\n")
        return path
