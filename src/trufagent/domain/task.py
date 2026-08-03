from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Level(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EffortLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModelTier(StrEnum):
    NONE = "none"
    ECONOMY = "economy"
    BALANCED = "balanced"
    FRONTIER = "frontier"


class Harness(StrEnum):
    CLAUDE = "claude"
    CODEX = "codex"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskMode(StrEnum):
    EXECUTION_DRIVEN = "execution-driven"
    DISCOVERY_DRIVEN = "discovery-driven"
    MIXED = "mixed"


class Reversibility(StrEnum):
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"


class AutonomyBoundary(StrEnum):
    PROCEED = "proceed"
    ANNOUNCE = "announce"
    CONFIRM = "confirm"
    BLOCK = "block"


class TaskKind(StrEnum):
    SMALL_CHANGE = "small-change"
    BUG = "bug"
    FEATURE = "feature"
    ARCHITECTURE = "architecture"
    DIAGNOSTIC = "diagnostic"
    VISUAL_REDESIGN = "visual-redesign"
    RESEARCH = "research"
    PLANNED_IMPLEMENTATION = "planned-implementation"


class TaskSignals(BaseModel):
    """Explicit evidence consumed by the deterministic classifier."""

    model_config = ConfigDict(extra="forbid")

    kind: TaskKind
    solution_known: bool = False
    cause_known: bool | None = None
    approved_plan: bool = False
    open_decisions: bool = False
    localized: bool = False
    multi_surface: bool = False
    persistence: bool = False
    permissions: bool = False
    secrets: bool = False
    production: bool = False
    silent_failure: bool = False
    shared_contract: bool = False
    shared_symptom: bool = False
    library_behavior: bool = False
    visual: bool = False
    approved_artifact: bool = False
    artifact_available: bool = True
    external_constraint: bool = False
    hypothesis_may_negate_work: bool = False
    integration_testing: bool = False
    state_logic: bool = False


class TaskProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: TaskMode
    ambiguity: Level
    risk: RiskLevel
    reversibility: Reversibility


class EffortBudgets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exploration: EffortLevel
    execution: EffortLevel
    verification: EffortLevel


class ModelRouting(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coordinator: ModelTier = ModelTier.ECONOMY
    exploration: ModelTier
    execution: ModelTier
    verification: ModelTier


class ContextSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rules: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    structural_targets: list[str] = Field(default_factory=list)


class TaskStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_profile: TaskProfile
    budgets: EffortBudgets
    context: ContextSelection = Field(default_factory=ContextSelection)
    skills: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)
    autonomy_boundary: AutonomyBoundary
    reasons: list[str] = Field(default_factory=list)
