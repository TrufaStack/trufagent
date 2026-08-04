from pathlib import Path

from trufagent.domain.skills import (
    SkillCatalogDocument,
    SkillCatalogEntry,
    SkillLocation,
)
from trufagent.experimental.codex_skill_surface import (
    apply_managed_skill_surface,
    plan_codex_skill_surface,
)


def _entry(name: str, path: Path, *, reviewed: bool) -> SkillCatalogEntry:
    return SkillCatalogEntry(
        id=f"{name}@{'a' * 12}",
        name=name,
        source="test",
        version="1",
        fingerprint="a" * 64,
        reviewed=reviewed,
        locations=[SkillLocation(platform="codex", path=str(path))],
    )


def test_surface_keeps_core_and_reviewed_skills_only(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    paths = {}
    for name in ("trufagent", "reviewed", "unreviewed"):
        paths[name] = root / name / "SKILL.md"
        paths[name].parent.mkdir(parents=True)
        paths[name].write_text(f"---\nname: {name}\ndescription: test\n---\n")
    catalog = SkillCatalogDocument(
        schema="trufagent.skills.v1",
        generated_at="2026-07-30T00:00:00Z",
        entries=[
            _entry("reviewed", paths["reviewed"], reviewed=True),
            _entry("unreviewed", paths["unreviewed"], reviewed=False),
        ],
    )

    surface = plan_codex_skill_surface(catalog, root)

    assert surface.daily == ["reviewed", "trufagent"]
    assert surface.library == ["unreviewed"]
    assert surface.disabled_paths == [paths["unreviewed"].resolve()]


def test_apply_preserves_user_config_and_replaces_managed_block(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('model = "demo"\n')
    catalog = SkillCatalogDocument(
        schema="trufagent.skills.v1",
        generated_at="2026-07-30T00:00:00Z",
        entries=[],
    )
    root = tmp_path / "skills"
    skill = root / "library-only" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: library-only\ndescription: test\n---\n")
    surface = plan_codex_skill_surface(catalog, root)

    apply_managed_skill_surface(config, surface)
    first = config.read_text()
    apply_managed_skill_surface(config, surface)
    second = config.read_text()

    assert first == second
    assert 'model = "demo"' in second
    assert second.count("BEGIN TRUFAGENT") == 1
    assert "enabled = false" in second
