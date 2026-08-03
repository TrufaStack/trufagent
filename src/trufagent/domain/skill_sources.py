from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class RemoteSkillFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    severity: Literal["warning", "critical"]
    code: str


class RemoteSkillCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    path: str
    fingerprint: str
    local_duplicate: bool = False
    findings: list[RemoteSkillFinding] = Field(default_factory=list)


class RemoteSkillSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: str = Field(pattern=r"^[^/]+/[^/]+$")
    url: HttpUrl
    trust: Literal["official", "community-reviewed", "discovery-only"]
    purpose: str
    stars: int = Field(ge=0)
    forks: int = Field(ge=0)
    license: str | None = None
    default_branch: str
    head_sha: str
    pushed_at: datetime
    observed_at: datetime
    enabled: bool = True
    skill_files: int = Field(default=0, ge=0)
    support_scripts: int = Field(default=0, ge=0)
    local_duplicates: int = Field(default=0, ge=0)
    warning_signals: int = Field(default=0, ge=0)
    critical_signals: int = Field(default=0, ge=0)
    findings: list[RemoteSkillFinding] = Field(default_factory=list)
    skills: list[RemoteSkillCandidate] = Field(default_factory=list)


class RemoteSkillRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["trufagent.skills.sources.v1"] = Field(
        default="trufagent.skills.sources.v1", alias="schema"
    )
    generated_at: datetime
    sources: list[RemoteSkillSource] = Field(default_factory=list)
