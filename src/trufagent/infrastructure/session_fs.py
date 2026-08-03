from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml

from trufagent.domain.session import SessionHandoff, SessionState


def _atomic_yaml(path: Path, model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(
        model.model_dump(by_alias=True, mode="json"),
        sort_keys=False,
        allow_unicode=True,
    )
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class FileSessionRepository:
    def __init__(self, project_root: Path) -> None:
        self.state_root = Path(project_root).resolve() / ".trufagent" / "state"
        self.current_path = self.state_root / "current-session.yaml"
        self.handoff_path = self.state_root / "handoff.yaml"
        self.sessions_root = self.state_root / "sessions"

    def current(self) -> SessionState | None:
        if not self.current_path.is_file():
            return None
        return SessionState.model_validate(
            yaml.safe_load(self.current_path.read_text(encoding="utf-8"))
        )

    def handoff(self) -> SessionHandoff | None:
        if not self.handoff_path.is_file():
            return None
        return SessionHandoff.model_validate(
            yaml.safe_load(self.handoff_path.read_text(encoding="utf-8"))
        )

    def save_current(self, state: SessionState) -> Path:
        _atomic_yaml(self.current_path, state)
        return self.current_path

    def close(
        self,
        state: SessionState,
        handoff: SessionHandoff,
        journal: str,
    ) -> Path:
        self.sessions_root.mkdir(parents=True, exist_ok=True)
        journal_path = self.sessions_root / f"{state.id}.md"
        try:
            with journal_path.open("x", encoding="utf-8") as handle:
                handle.write(journal)
        except FileExistsError as exc:
            raise FileExistsError(f"session journal already exists: {journal_path}") from exc
        _atomic_yaml(self.handoff_path, handoff)
        self.current_path.unlink()
        return journal_path
