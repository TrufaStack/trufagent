from __future__ import annotations

from pathlib import Path

import pytest

from trufagent.domain.memory import MemoryScope
from trufagent.infrastructure.memory_fs import (
    PROTECTIVE_GITIGNORE,
    MarkdownMemoryRepository,
    MemoryAlreadyExistsError,
    MemoryIsolationError,
    MemoryVaultError,
)
from trufagent.infrastructure.memory_markdown import load_memory_markdown

FIXTURES = Path(__file__).parent / "fixtures" / "memory"


def fixture(name: str):
    return load_memory_markdown(FIXTURES / name)


def test_initialize_creates_protected_vault(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(tmp_path, project="jc-app")

    repository.initialize()

    vault = tmp_path / ".trufagent"
    assert (vault / "memory" / "project").is_dir()
    assert (vault / "memory" / "team").is_dir()
    assert (vault / "state").is_dir()
    assert (vault / "cartography").is_dir()
    assert (vault / ".gitignore").read_text() == PROTECTIVE_GITIGNORE


def test_initialize_fails_closed_if_protection_was_modified(tmp_path: Path) -> None:
    vault = tmp_path / ".trufagent"
    vault.mkdir()
    (vault / ".gitignore").write_text("# user changed this\n")

    with pytest.raises(MemoryVaultError, match="protection"):
        MarkdownMemoryRepository(tmp_path, project="jc-app").initialize()


def test_propose_is_create_only_and_keeps_project_memory_local(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(tmp_path, project="jc-app")
    repository.initialize()
    document = fixture("c02-checklist-risk.md")

    created = repository.propose(document)

    assert created.parent == tmp_path / ".trufagent" / "memory" / "team"
    assert repository.read(document.envelope.id).envelope.status.value == "accepted"
    with pytest.raises(MemoryAlreadyExistsError):
        repository.propose(document)


def test_repository_rejects_memory_for_another_project(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(tmp_path, project="another-project")
    repository.initialize()

    with pytest.raises(MemoryIsolationError):
        repository.propose(fixture("c02-checklist-risk.md"))


def test_search_defaults_to_project_and_team_but_user_is_explicit(tmp_path: Path) -> None:
    user_root = tmp_path / "user-memory"
    repository = MarkdownMemoryRepository(
        tmp_path / "repo", project="jc-app", user_memory_root=user_root
    )
    repository.initialize()
    repository.propose(fixture("c02-checklist-risk.md"))
    repository.propose(fixture("c05-safe-diagnostics-rule.md"))
    default_results = repository.search("checklist environment")
    explicit_results = repository.search("checklist environment", include_user=True)

    assert {item.envelope.scope for item in default_results} == {MemoryScope.TEAM}
    assert MemoryScope.USER in {item.envelope.scope for item in explicit_results}


def test_normal_search_excludes_rejected_superseded_and_stale(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(tmp_path, project="jc-app")
    repository.initialize()
    original = (FIXTURES / "c10-mobile-artifact.md").read_text()
    for status in ("rejected", "superseded", "stale"):
        text = original.replace("mem_C10_MOBILE_ARTIFACT", f"mem_mobile_{status}")
        text = text.replace("status: proposed", f"status: {status}")
        if status == "superseded":
            text = text.replace("superseded_by: []", "superseded_by: [mem_replacement]")
        path = tmp_path / f"{status}.md"
        path.write_text(text)
        repository.propose(load_memory_markdown(path))

    assert repository.search("mobile navigation artifact") == []
