from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def _skill(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_plugin_manifest_describes_v1_runtime() -> None:
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())

    assert plugin["version"] == "0.4.0"
    assert "context-aware effort orchestration" in plugin["description"].lower()
    assert marketplace["plugins"][0]["version"] == "0.4.0"
    assert "litellm" not in json.dumps([plugin, marketplace]).lower()


def test_claude_adapter_exposes_three_thin_skills() -> None:
    for name in ("trufagent", "start-session", "end-session"):
        document = _skill(name)
        frontmatter = yaml.safe_load(document.split("---", 2)[1])
        assert frontmatter["name"] == name
        assert "${CLAUDE_PLUGIN_ROOT}" in document
        assert "uv run --project" in document


def test_task_adapter_delegates_policy_to_runtime() -> None:
    document = _skill("trufagent").lower()

    assert "trufagent prepare" in document
    assert "needs_input" in document
    assert "questions" in document
    assert "`model_tier`" in document
    assert "host owns coordination" in document
    assert "models resolve" in document
    assert "required_symbols" in document
    assert "graphify-first" in document.lower()
    assert "delegation compile" not in document
    assert "delegation dry-run" not in document
    assert "shadow" not in document
    assert "do not invent" in document
    for legacy in ("litellm", "scout", "docs/context", "auto-commit"):
        assert legacy not in document


def test_session_adapters_do_not_commit_or_create_parallel_memory() -> None:
    start = _skill("start-session").lower()
    end = _skill("end-session").lower()

    assert "session start" in start
    assert "session end" in end
    assert "never run git commit" in end
    assert "memory_proposals" in end
    assert "proposed" in end
    assert "docs/context" not in start + end


def test_legacy_init_and_status_are_safe_v1_adapters() -> None:
    init = _skill("init").lower()
    status = _skill("status").lower()

    assert "trufagent init" in init
    assert "read-only" in status
    for legacy in ("litellm", "server.py", "docs/context"):
        assert legacy not in init + status
