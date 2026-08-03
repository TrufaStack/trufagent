from __future__ import annotations

import json
from pathlib import Path

from trufagent.application.skill_sanitization import (
    apply_skill_sanitization,
    plan_skill_sanitization,
)
from trufagent.cli import main
from trufagent.infrastructure.skill_audit import audit_skill_catalog
from trufagent.infrastructure.skill_catalog_fs import SkillCatalogRepository
from trufagent.infrastructure.skill_discovery import SkillDiscovery


def _skill(root: Path, folder: str, name: str, description: str) -> None:
    path = root / folder / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# Instructions\n",
        encoding="utf-8",
    )


def _documents(tmp_path: Path):
    root = tmp_path / "skills"
    _skill(root, "debug", "systematic-debugging", "Debug unexpected failures safely")
    _skill(root, "legacy", "configure-ecc", "Install legacy agent configuration")
    _skill(root, "mobile", "flutter-review", "Review Flutter mobile applications")
    catalog = SkillDiscovery({"codex": root}).scan().catalog
    next(entry for entry in catalog.entries if entry.name == "systematic-debugging").reviewed = True
    return catalog, audit_skill_catalog(catalog)


def test_plan_is_conservative_and_never_moves_files(tmp_path: Path) -> None:
    catalog, audit = _documents(tmp_path)

    manifest = plan_skill_sanitization(
        catalog, audit, archive_root=tmp_path / "archive" / "v1"
    )
    by_name = {entry.name: entry for entry in manifest.entries}

    assert by_name["systematic-debugging"].tier == "core"
    assert by_name["flutter-review"].tier == "cold"
    assert by_name["configure-ecc"].tier == "quarantine"
    assert by_name["configure-ecc"].proposed_action == "archive"
    current_paths = [path for entry in manifest.entries for path in entry.current_locations]
    assert all(Path(path).exists() for path in current_paths)


def test_cli_writes_plan_with_zero_mutations(tmp_path: Path, capsys) -> None:
    catalog, audit = _documents(tmp_path)
    catalog_path = tmp_path / "catalog.yaml"
    audit_path = tmp_path / "audit.json"
    manifest_path = tmp_path / "manifest.json"
    SkillCatalogRepository(catalog_path).save(catalog)
    audit_path.write_text(audit.model_dump_json(by_alias=True), encoding="utf-8")

    exit_code = main(
        [
            "skills",
            "sanitize",
            "--plan",
            "--catalog",
            str(catalog_path),
            "--audit",
            str(audit_path),
            "--manifest",
            str(manifest_path),
        ]
    )
    result = json.loads(capsys.readouterr().out)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert result["mutations"] == 0
    assert manifest["mode"] == "plan"
    assert len(manifest["entries"]) == 3


def test_host_specific_variants_can_both_be_canonical(tmp_path: Path) -> None:
    codex = tmp_path / "codex"
    claude = tmp_path / "claude"
    _skill(codex, "adapter", "trufagent", "Codex task preparation adapter")
    _skill(claude, "adapter", "trufagent", "Claude task preparation adapter")
    catalog = SkillDiscovery({"codex": codex, "claude": claude}).scan().catalog
    for entry in catalog.entries:
        entry.reviewed = True
    audit = audit_skill_catalog(catalog)

    manifest = plan_skill_sanitization(catalog, audit, archive_root=tmp_path / "archive")

    assert len(manifest.entries) == 2
    assert all(entry.canonical_for_host for entry in manifest.entries)


def test_apply_moves_local_quarantine_to_recoverable_archive(tmp_path: Path) -> None:
    catalog, audit = _documents(tmp_path)
    root = tmp_path / "skills"
    archive = tmp_path / "archive" / "v1"
    manifest = plan_skill_sanitization(catalog, audit, archive_root=archive)

    result = apply_skill_sanitization(manifest, catalog, movable_roots=[root])
    legacy = next(entry for entry in catalog.entries if entry.name == "configure-ecc")
    archived = archive / "codex" / f"configure-ecc@{legacy.fingerprint[:12]}"

    assert result == {"moved": 1, "quarantined": 1}
    assert archived.joinpath("SKILL.md").is_file()
    assert legacy.quarantined is True
    assert legacy.active is False

    resumed = apply_skill_sanitization(manifest, catalog, movable_roots=[root])
    assert resumed == {"moved": 0, "quarantined": 1}
