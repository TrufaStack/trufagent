from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trufagent.domain.task import ModelTier


class PrepareStatus(StrEnum):
    READY = "ready"
    NEEDS_INPUT = "needs_input"


class Complexity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PhaseEffort(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SkillPhase(StrEnum):
    EXPLORE = "explore"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    ANY = "any"


class PrepareTaskSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["small-change", "fix", "feature", "research", "architecture"]
    complexity: Complexity


class PrepareEffort(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explore: PhaseEffort
    implement: PhaseEffort
    verify: PhaseEffort


class PrepareSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    phase: SkillPhase
    location: str | None = None
    platform: str | None = None


class PrepareMemoryReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    estimated_tokens: int = Field(ge=0)
    memory_schema: Literal["trufagent.memory.v1", "trufagent.memory.v2"]
    source_commit: str | None = None


class PrepareGraphReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    source_file: str | None = None


class PrepareContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memories: list[PrepareMemoryReference] = Field(default_factory=list)
    graph: list[PrepareGraphReference] = Field(default_factory=list)
    estimated_tokens: int = Field(default=0, ge=0)
    omitted_count: int = Field(default=0, ge=0)


class PrepareQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1)
    prompt: str = Field(min_length=1)


class PrepareV2Result(BaseModel):
    """Compact host-facing contract for Trufagent v2 task preparation."""

    model_config = ConfigDict(extra="forbid")

    schema_: Literal["trufagent.prepare.v2"] = Field(
        default="trufagent.prepare.v2",
        alias="schema",
    )
    status: PrepareStatus
    task: PrepareTaskSummary | None = None
    model_tier: ModelTier | None = None
    effort: PrepareEffort | None = None
    skills: list[PrepareSkill] = Field(default_factory=list)
    context: PrepareContext = Field(default_factory=PrepareContext)
    questions: list[PrepareQuestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
