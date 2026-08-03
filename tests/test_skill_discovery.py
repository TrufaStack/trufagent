from __future__ import annotations

from pathlib import Path

from trufagent.application.skill_catalog import InMemorySkillCatalog
from trufagent.domain.skills import SkillCatalogDocument
from trufagent.infrastructure.skill_catalog_fs import SkillCatalogRepository
from trufagent.infrastructure.skill_discovery import SkillDiscovery


def write_skill(root: Path, folder: str, name: str, body: str = "# Instructions") -> Path:
    path = root / folder / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"---\nname: {name}\ndescription: Test skill {name}\n---\n\n{body}\n")
    return path


def test_discovery_deduplicates_identical_copies_and_combines_locations(
    tmp_path: Path,
) -> None:
    claude = tmp_path / "claude"
    codex = tmp_path / "codex"
    write_skill(claude, "debug", "systematic-debugging")
    write_skill(codex, "debug-copy", "systematic-debugging")

    result = SkillDiscovery({"claude": claude, "codex": codex}).scan()

    assert len(result.catalog.entries) == 1
    entry = result.catalog.entries[0]
    assert entry.name == "systematic-debugging"
    assert {location.platform for location in entry.locations} == {"claude", "codex"}
    assert entry.reviewed is False
    assert entry.active is True


def test_same_name_with_different_content_is_inactive_conflict(tmp_path: Path) -> None:
    claude = tmp_path / "claude"
    codex = tmp_path / "codex"
    write_skill(claude, "debug", "systematic-debugging", "# Claude variant")
    write_skill(codex, "debug", "systematic-debugging", "# Codex variant")

    result = SkillDiscovery({"claude": claude, "codex": codex}).scan()

    assert len(result.catalog.entries) == 2
    assert all(entry.active is False for entry in result.catalog.entries)
    assert any("systematic-debugging" in warning for warning in result.warnings)


def test_sync_preserves_review_only_for_unchanged_fingerprint(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    path = write_skill(skills, "debug", "systematic-debugging")
    repository = SkillCatalogRepository(tmp_path / "catalog.yaml")
    first = SkillDiscovery({"codex": skills}).scan().catalog
    first.entries[0].reviewed = True
    repository.save(first)

    unchanged = repository.sync(SkillDiscovery({"codex": skills}).scan().catalog)
    assert unchanged.entries[0].reviewed is True

    path.write_text(path.read_text().replace("# Instructions", "# Changed instructions"))
    changed = repository.sync(SkillDiscovery({"codex": skills}).scan().catalog)
    assert changed.entries[0].reviewed is False


def test_only_active_reviewed_entries_reach_runtime_catalog(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    write_skill(skills, "debug", "systematic-debugging")
    document = SkillDiscovery({"codex": skills}).scan().catalog
    document.entries[0].reviewed = True

    runtime = InMemorySkillCatalog.from_document(document)

    assert runtime.select(["systematic-debugging"]).selected[0].name == "systematic-debugging"


def test_catalog_yaml_round_trip(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    write_skill(skills, "debug", "systematic-debugging")
    catalog = SkillDiscovery({"codex": skills}).scan().catalog
    repository = SkillCatalogRepository(tmp_path / "catalog.yaml")

    repository.save(catalog)
    loaded = repository.load()

    assert isinstance(loaded, SkillCatalogDocument)
    assert loaded == catalog


def test_review_can_activate_one_conflicting_variant(tmp_path: Path) -> None:
    claude = tmp_path / "claude"
    codex = tmp_path / "codex"
    write_skill(claude, "debug", "systematic-debugging", "# Claude")
    write_skill(codex, "debug", "systematic-debugging", "# Codex")
    repository = SkillCatalogRepository(tmp_path / "catalog.yaml")
    catalog = SkillDiscovery({"claude": claude, "codex": codex}).scan().catalog
    repository.save(catalog)
    chosen = catalog.entries[0]

    reviewed = repository.review(chosen.id, activate=True)

    variants = [entry for entry in reviewed.entries if entry.name == chosen.name]
    assert sum(entry.active for entry in variants) == 1
    assert next(entry for entry in variants if entry.active).reviewed is True

    synced = repository.sync(SkillDiscovery({"claude": claude, "codex": codex}).scan().catalog)
    variants = [entry for entry in synced.entries if entry.name == chosen.name]
    assert sum(entry.active for entry in variants) == 1
    assert next(entry for entry in variants if entry.active).id == chosen.id


def test_malformed_frontmatter_falls_back_to_folder_name(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    path = root / "legacy-skill" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\ndescription: broken: yaml\n---\n# Legacy")

    result = SkillDiscovery({"claude": root}).scan()

    assert result.catalog.entries[0].name == "legacy-skill"
