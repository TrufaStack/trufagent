from __future__ import annotations

import json
from pathlib import Path

from trufagent.application.skill_catalog import InMemorySkillCatalog
from trufagent.cli import main
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


def test_same_name_with_host_specific_content_is_not_a_conflict(tmp_path: Path) -> None:
    claude = tmp_path / "claude"
    codex = tmp_path / "codex"
    write_skill(claude, "debug", "systematic-debugging", "# Claude variant")
    write_skill(codex, "debug", "systematic-debugging", "# Codex variant")

    result = SkillDiscovery({"claude": claude, "codex": codex}).scan()

    assert len(result.catalog.entries) == 2
    assert all(entry.active is True for entry in result.catalog.entries)
    assert not any("systematic-debugging" in warning for warning in result.warnings)


def test_same_name_with_different_content_on_one_host_is_a_conflict(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_skill(first, "debug", "systematic-debugging", "# First Codex variant")
    write_skill(second, "debug", "systematic-debugging", "# Second Codex variant")

    result = SkillDiscovery(
        {"codex-primary": first, "codex-secondary": second}
    ).scan()

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


def test_sync_preserves_quarantine_for_unchanged_fingerprint(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    write_skill(skills, "legacy", "legacy-workflow")
    repository = SkillCatalogRepository(tmp_path / "catalog.yaml")
    catalog = SkillDiscovery({"codex": skills}).scan().catalog
    catalog.entries[0].quarantined = True
    catalog.entries[0].active = False
    repository.save(catalog)

    synced = repository.sync(SkillDiscovery({"codex": skills}).scan().catalog)

    assert synced.entries[0].quarantined is True
    assert synced.entries[0].active is False


def test_only_active_reviewed_entries_reach_runtime_catalog(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    write_skill(skills, "debug", "systematic-debugging")
    document = SkillDiscovery({"codex": skills}).scan().catalog
    document.entries[0].reviewed = True

    runtime = InMemorySkillCatalog.from_document(document)

    assert runtime.select(["systematic-debugging"]).selected[0].name == "systematic-debugging"


def test_runtime_library_prefers_a_location_for_the_requested_harness(tmp_path: Path) -> None:
    claude = tmp_path / "claude"
    codex = tmp_path / "codex"
    write_skill(claude, "debug", "systematic-debugging")
    write_skill(codex, "debug", "systematic-debugging")
    document = SkillDiscovery({"claude": claude, "codex": codex}).scan().catalog
    document.entries[0].reviewed = True
    library = InMemorySkillCatalog.from_document(document)

    selected = library.select(["systematic-debugging"]).selected[0]

    assert selected.location_for("codex").path == str(
        (codex / "debug" / "SKILL.md").resolve()
    )
    assert selected.location_for("claude").path == str(
        (claude / "debug" / "SKILL.md").resolve()
    )


def test_runtime_library_searches_reviewed_skills_by_capability(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "debug", "systematic-debugging")
    write_skill(root, "ideas", "brainstorming")
    document = SkillDiscovery({"codex": root}).scan().catalog
    for entry in document.entries:
        entry.reviewed = entry.name == "systematic-debugging"
    library = InMemorySkillCatalog.from_document(document)

    matches = library.search("systematic debugging unexpected behavior", harness="codex")

    assert [match.skill.name for match in matches] == ["systematic-debugging"]
    assert matches[0].location.platform == "codex"
    assert "debugging" in matches[0].matched_terms

    all_matches = library.search("brainstorming ideas", reviewed_only=False)
    assert [match.skill.name for match in all_matches] == ["brainstorming"]
    assert all_matches[0].skill.reviewed is False


def test_cli_search_exposes_host_aware_capability_matches(tmp_path: Path, capsys) -> None:
    root = tmp_path / "skills"
    write_skill(root, "debug", "systematic-debugging")
    catalog = SkillDiscovery({"codex": root}).scan().catalog
    catalog.entries[0].reviewed = True
    catalog_path = tmp_path / "catalog.yaml"
    SkillCatalogRepository(catalog_path).save(catalog)

    exit_code = main(
        [
            "skills",
            "search",
            "systematic debugging",
            "--harness",
            "codex",
            "--catalog",
            str(catalog_path),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["schema"] == "trufagent.skills.search.v2"
    assert output["matches"][0]["skill"]["name"] == "systematic-debugging"
    assert output["matches"][0]["location"]["platform"] == "codex"


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
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_skill(first, "debug", "systematic-debugging", "# First Codex variant")
    write_skill(second, "debug", "systematic-debugging", "# Second Codex variant")
    repository = SkillCatalogRepository(tmp_path / "catalog.yaml")
    roots = {"codex-primary": first, "codex-secondary": second}
    catalog = SkillDiscovery(roots).scan().catalog
    repository.save(catalog)
    chosen = catalog.entries[0]

    reviewed = repository.review(chosen.id, activate=True)

    variants = [entry for entry in reviewed.entries if entry.name == chosen.name]
    assert sum(entry.active for entry in variants) == 1
    assert next(entry for entry in variants if entry.active).reviewed is True

    synced = repository.sync(SkillDiscovery(roots).scan().catalog)
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
