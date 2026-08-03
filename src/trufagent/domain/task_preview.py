from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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
