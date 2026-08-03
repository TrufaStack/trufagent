from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trufagent.application.skill_import import plan_skill_import
from trufagent.domain.skill_sources import (
    RemoteSkillCandidate,
    RemoteSkillRegistry,
    RemoteSkillSource,
)


def _registry() -> RemoteSkillRegistry:
    now = datetime.now(UTC)
    return RemoteSkillRegistry(
        generated_at=now,
        sources=[
            RemoteSkillSource(
                repository="example/skills",
                url="https://github.com/example/skills",
                trust="community-reviewed",
                purpose="testing",
                stars=10,
                forks=2,
                license="MIT",
                default_branch="main",
                head_sha="a" * 40,
                pushed_at=now,
                observed_at=now,
                skills=[
                    RemoteSkillCandidate(
                        name="review-code",
                        path="repo/skills/review-code/SKILL.md",
                        fingerprint="b" * 64,
                    ),
                    RemoteSkillCandidate(
                        name="duplicate",
                        path="repo/skills/duplicate/SKILL.md",
                        fingerprint="c" * 64,
                        local_duplicate=True,
                    ),
                ],
            )
        ],
    )


def test_plan_separates_direct_imports_from_adaptations(tmp_path: Path) -> None:
    manifest = plan_skill_import(
        _registry(),
        direct=["example/skills:review-code"],
        adapt=["example/skills:duplicate"],
        vendor_root=tmp_path / "vendor",
        adaptation_root=tmp_path / "adapted",
    )

    direct, adapt = manifest.items
    assert direct.mode == "direct"
    assert direct.status == "candidate"
    assert direct.commit == "a" * 40
    assert adapt.mode == "adapt"
    assert adapt.status == "rejected"
    assert adapt.reasons == ["exact-local-duplicate"]


def test_plan_rejects_sources_outside_governed_registry(tmp_path: Path) -> None:
    try:
        plan_skill_import(
            _registry(),
            direct=["unknown/skills:review-code"],
            adapt=[],
            vendor_root=tmp_path / "vendor",
            adaptation_root=tmp_path / "adapted",
        )
    except ValueError as exc:
        assert "not in the governed registry" in str(exc)
    else:
        raise AssertionError("expected unknown repository to be rejected")
