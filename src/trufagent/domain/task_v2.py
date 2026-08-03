from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from trufagent.domain.prepare_v2 import Complexity, PrepareEffort
from trufagent.domain.task import ModelTier


class TaskKindV2(StrEnum):
    SMALL_CHANGE = "small-change"
    FIX = "fix"
    FEATURE = "feature"
    RESEARCH = "research"
    ARCHITECTURE = "architecture"


class Uncertainty(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskScope(StrEnum):
    LOCAL = "local"
    BROAD = "broad"


class TaskRisk(StrEnum):
    NORMAL = "normal"
    HIGH = "high"


class StructuralContext(StrEnum):
    NONE = "none"
    USEFUL = "useful"
    REQUIRED = "required"


class TaskSignalsV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: TaskKindV2
    uncertainty: Uncertainty
    scope: TaskScope = TaskScope.LOCAL
    risk: TaskRisk = TaskRisk.NORMAL
    open_decisions: bool = False
    structural_context: StructuralContext = StructuralContext.NONE


class SkillRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class TaskClassificationV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complexity: Complexity
    model_tier: ModelTier
    effort: PrepareEffort
    skills: list[SkillRecommendation] = Field(default_factory=list)
    query_graph: bool = False
    reasons: list[str] = Field(default_factory=list)
