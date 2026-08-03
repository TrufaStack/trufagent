from pathlib import Path

import pytest
from pydantic import ValidationError

from trufagent.domain.task import ModelTier
from trufagent.infrastructure.model_profiles import (
    Harness,
    load_model_overrides,
    resolve_model,
    resolve_project_model,
    resolve_reasoning_effort,
)


def test_codex_economy_uses_validated_luna_profile() -> None:
    assert resolve_model(Harness.CODEX, ModelTier.ECONOMY) == "gpt-5.6-luna"
    assert resolve_reasoning_effort(Harness.CODEX, ModelTier.ECONOMY) == "max"


def test_codex_balanced_and_frontier_use_sol_low() -> None:
    for tier in (ModelTier.BALANCED, ModelTier.FRONTIER):
        assert resolve_model(Harness.CODEX, tier) == "gpt-5.6-sol"
        assert resolve_reasoning_effort(Harness.CODEX, tier) == "low"


def test_claude_economy_stays_on_sonnet_after_haiku_canary_failed() -> None:
    assert resolve_model(Harness.CLAUDE, ModelTier.ECONOMY) == "sonnet"


def test_none_tier_does_not_invoke_a_model() -> None:
    assert resolve_model(Harness.CODEX, ModelTier.NONE) is None
    assert resolve_model(Harness.CLAUDE, ModelTier.NONE) is None


def test_project_can_override_one_profile_without_copying_defaults(tmp_path: Path) -> None:
    config = tmp_path / ".trufagent" / "config.yaml"
    config.parent.mkdir()
    config.write_text(
        "schema: trufagent.project.v1\nproject: demo\nmodels:\n  codex:\n    balanced: gpt-custom\n"
    )

    resolved = resolve_project_model(tmp_path, Harness.CODEX, ModelTier.BALANCED)

    assert resolved.model == "gpt-custom"
    assert resolved.reasoning_effort == "low"
    assert resolved.source == "project"
    assert (
        resolve_model(
            Harness.CODEX,
            ModelTier.ECONOMY,
            load_model_overrides(tmp_path),
        )
        == "gpt-5.6-luna"
    )


def test_project_cannot_override_unknown_tiers(tmp_path: Path) -> None:
    config = tmp_path / ".trufagent" / "config.yaml"
    config.parent.mkdir()
    config.write_text("models:\n  codex:\n    cheapest: mystery\n")

    with pytest.raises(ValidationError, match="cheapest"):
        load_model_overrides(tmp_path)
