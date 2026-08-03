from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SkillLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: str = Field(min_length=1)
    path: str = Field(min_length=1)


class SkillCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    source: str = Field(min_length=1)
    version: str = Field(min_length=1)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed: bool = False
    active: bool = True
    available: bool = True
    quarantined: bool = False
    locations: list[SkillLocation] = Field(default_factory=list)


class SkillCatalogDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.skills\.v1$")
    generated_at: datetime
    entries: list[SkillCatalogEntry] = Field(default_factory=list)
