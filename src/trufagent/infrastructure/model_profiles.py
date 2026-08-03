from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from trufagent.domain.task import Harness, ModelTier

_MODELS: dict[Harness, dict[ModelTier, str | None]] = {
    Harness.CLAUDE: {
        ModelTier.NONE: None,
        # Haiku failed the C01 autonomy and no-diagnostic-command judges.
        ModelTier.ECONOMY: "sonnet",
        ModelTier.BALANCED: "sonnet",
        ModelTier.FRONTIER: "opus",
    },
    Harness.CODEX: {
        ModelTier.NONE: None,
        ModelTier.ECONOMY: "gpt-5.6-luna",
        ModelTier.BALANCED: "gpt-5.6-terra",
        ModelTier.FRONTIER: "gpt-5.6-sol",
    },
}


class TierOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    economy: str | None = Field(default=None, min_length=1)
    balanced: str | None = Field(default=None, min_length=1)
    frontier: str | None = Field(default=None, min_length=1)


class ModelProfileOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claude: TierOverrides = Field(default_factory=TierOverrides)
    codex: TierOverrides = Field(default_factory=TierOverrides)


class ResolvedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    harness: Harness
    tier: ModelTier
    model: str | None
    source: str


def load_model_overrides(project_root: Path) -> ModelProfileOverrides:
    config_path = Path(project_root) / ".trufagent" / "config.yaml"
    if not config_path.is_file():
        return ModelProfileOverrides()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"project configuration must be a mapping: {config_path}")
    return ModelProfileOverrides.model_validate(raw.get("models") or {})


def resolve_model(
    harness: Harness,
    tier: ModelTier,
    overrides: ModelProfileOverrides | None = None,
) -> str | None:
    """Resolve a policy tier to a harness model validated for that role."""

    if tier == ModelTier.NONE:
        return None
    if overrides is not None:
        model = getattr(getattr(overrides, harness.value), tier.value)
        if model is not None:
            return model
    return _MODELS[harness][tier]


def resolve_project_model(
    project_root: Path,
    harness: Harness,
    tier: ModelTier,
) -> ResolvedModel:
    overrides = load_model_overrides(project_root)
    configured = (
        None if tier == ModelTier.NONE else getattr(getattr(overrides, harness.value), tier.value)
    )
    return ResolvedModel(
        harness=harness,
        tier=tier,
        model=resolve_model(harness, tier, overrides),
        source="project" if configured is not None else "default",
    )
