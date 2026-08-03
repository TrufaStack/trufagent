from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillImportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: str
    commit: str
    license: str | None = None
    source_name: str
    source_path: str
    source_fingerprint: str
    mode: Literal["direct", "adapt"]
    destination: str
    local_duplicate: bool = False
    findings: list[str] = Field(default_factory=list)
    status: Literal["candidate", "needs-review", "rejected"]
    reasons: list[str] = Field(default_factory=list)


class SkillImportManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["trufagent.skills.import.v1"] = Field(
        default="trufagent.skills.import.v1", alias="schema"
    )
    generated_at: datetime
    mode: Literal["plan"] = "plan"
    items: list[SkillImportItem] = Field(default_factory=list)

