from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillAuditFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["info", "warning", "critical"]
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class SkillAuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: str
    name: str
    fingerprint: str
    reviewed: bool = False
    score: int = Field(ge=0, le=100)
    disposition: Literal["candidate", "review", "blocked"]
    files: int = Field(ge=0)
    scripts: int = Field(ge=0)
    findings: list[SkillAuditFinding] = Field(default_factory=list)


class SkillAuditReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["trufagent.skills.audit.v1"] = Field(
        default="trufagent.skills.audit.v1", alias="schema"
    )
    generated_at: datetime
    catalog_generated_at: datetime
    entries: list[SkillAuditEntry] = Field(default_factory=list)
