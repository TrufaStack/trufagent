from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
SKILLS = ROOT / "adapters" / "codex" / "skills"


def _documents(name: str) -> tuple[dict, str, dict]:
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(text.split("---", 2)[1])
    interface = yaml.safe_load(
        (SKILLS / name / "agents" / "openai.yaml").read_text(encoding="utf-8")
    )
    return frontmatter, text, interface


def test_codex_adapter_has_native_metadata_for_three_skills() -> None:
    for name in ("trufagent", "start-session", "end-session"):
        frontmatter, text, metadata = _documents(name)
        assert frontmatter.keys() == {"name", "description"}
        assert frontmatter["name"] == name
        assert "TODO" not in text
        assert metadata["interface"]["default_prompt"].startswith(f"Use ${name}")


def test_codex_task_skill_delegates_policy_to_runtime() -> None:
    _, text, _ = _documents("trufagent")
    lowered = text.lower()

    assert "trufagent plan prepare" in text
    assert "ready_to_plan" in text
    assert "questions" in text
    assert "do not invent signal overrides" in lowered
    assert "graphify" in lowered
    assert "first accessible `locations` path" in lowered
    assert "do not enable or scan the full skill library" in lowered
    assert "`model_route`" in lowered
    assert "host owns coordination" in lowered
    assert "coordinator=none" in lowered
    assert "models resolve" in lowered
    assert "required_symbols" in lowered
    assert "graphify-first" in lowered
    assert "delegation compile" in lowered
    assert "delegation dry-run" in lowered
    assert "shadow" in lowered
    assert "not enabled yet" in lowered
    for legacy in ("litellm", "scout", "docs/context", "auto-commit"):
        assert legacy not in lowered


def test_codex_session_skills_preserve_safety_boundaries() -> None:
    _, start, _ = _documents("start-session")
    _, end, _ = _documents("end-session")
    lowered = (start + end).lower()

    assert "trufagent session start" in start
    assert "trufagent session end" in end
    assert "memory_proposals" in end
    assert "never run `git commit`" in end.lower()
    assert "docs/context" not in lowered
