from pathlib import Path


def test_shadow_canary_script_disables_mutating_phases() -> None:
    script = (Path(__file__).parents[2] / "scripts" / "run_shadow_canary.py").read_text()

    assert "coordinator=ModelTier.NONE" in script
    assert "exploration=ModelTier.BALANCED" in script
    assert "execution=ModelTier.NONE" in script
    assert "verification=ModelTier.NONE" in script
    assert "ShadowPhaseAdapter" in script
    assert "evaluate_graphify_first" in script
    assert "evaluate_graphify_applicability" in script
    assert '"--signals"' in script
    assert '"graph_queries": graph_queries' in script
    assert "model_invocations" in script
    assert "allow_shadow" in script
