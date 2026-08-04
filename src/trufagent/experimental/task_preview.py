from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trufagent.domain.task import AutonomyBoundary, ModelRouting, TaskSignals


class TaskPreviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.task-preview-record\.v1$")
    preview_id: str = Field(pattern=r"^tp_[0-9a-f]{20}$")
    session_id: str
    project: str
    task_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    worktree_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    summary: str
    signals: TaskSignals
    route: ModelRouting
    skills: tuple[str, ...] = ()
    memory_ids: tuple[str, ...] = ()
    required_symbols: tuple[str, ...] = ()
    structural_targets: tuple[str, ...] = ()
    graph_state: str | None = None
    graph_commit: str | None = None
    graphify_version: str | None = None
    warnings: tuple[str, ...] = ()
    autonomy: AutonomyBoundary
    evidence_required: tuple[str, ...] = ()
    exploration_disposition: str | None = None
    exploration_reasons: tuple[str, ...] = ()


class TaskPreviewError(RuntimeError):
    pass


class FileTaskPreviewRepository:
    def __init__(self, project_root: Path) -> None:
        self.root = Path(project_root) / ".trufagent" / "state" / "task-previews"

    def path_for(self, preview_id: str) -> Path:
        return self.root / f"{preview_id}.json"

    def save(self, preview: TaskPreviewRecord) -> Path:
        path = self.path_for(preview.preview_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = preview.model_dump_json(by_alias=True, indent=2) + "\n"
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        except FileExistsError:
            existing = self.read(preview.preview_id)
            if existing != preview:
                raise TaskPreviewError(
                    f"task preview already exists: {preview.preview_id}"
                ) from None
        return path

    def read(self, preview_id: str) -> TaskPreviewRecord:
        path = self.path_for(preview_id)
        try:
            return TaskPreviewRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise TaskPreviewError(f"task preview not found: {preview_id}") from exc
        except (OSError, ValidationError) as exc:
            raise TaskPreviewError(f"invalid task preview: {path}") from exc
