from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.session\.v1$")
    id: str = Field(pattern=r"^ses_[A-Za-z0-9_-]{6,80}$")
    project: str = Field(min_length=1)
    started_at: datetime
    updated_at: datetime
    objective: str | None = None


class SessionHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.handoff\.v1$")
    from_session: str
    project: str
    closed_at: datetime
    summary: str = Field(min_length=1)
    completed: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    proposed_memory_ids: list[str] = Field(default_factory=list)
