from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillSanitizationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: str
    name: str
    fingerprint: str
    capability: str
    tier: Literal["core", "profile", "cold", "quarantine"]
    canonical_for_host: bool = False
    reviewed: bool = False
    active: bool = True
    reasons: list[str] = Field(default_factory=list)
    current_locations: list[str] = Field(default_factory=list)
    proposed_action: Literal["keep-active", "keep-cold", "archive"]
    proposed_archive_root: str | None = None


class SkillSanitizationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["trufagent.skills.sanitization.v1"] = Field(
        default="trufagent.skills.sanitization.v1", alias="schema"
    )
    generated_at: datetime
    catalog_generated_at: datetime
    audit_generated_at: datetime
    mode: Literal["plan"] = "plan"
    entries: list[SkillSanitizationEntry] = Field(default_factory=list)
