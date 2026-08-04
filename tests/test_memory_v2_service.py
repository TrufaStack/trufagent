from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trufagent.application.memory_v2 import MemoryV2Service
from trufagent.cli import main
from trufagent.domain.memory import MemoryKind
from trufagent.domain.memory_v2 import MemoryStateV2
from trufagent.infrastructure.memory_fs import MemoryAlreadyExistsError
from trufagent.infrastructure.memory_index import SqliteMemoryIndex
from trufagent.infrastructure.memory_v2_fs import MarkdownMemoryRepositoryV2

NOW = datetime(2026, 8, 4, 1, 0, tzinfo=UTC)


def setup(tmp_path: Path):
    repository = MarkdownMemoryRepositoryV2(tmp_path, project="demo").initialize()
    index = SqliteMemoryIndex(tmp_path / ".trufagent/memory-index.sqlite3")
    service = MemoryV2Service(repository, index=index, clock=lambda: NOW)
    return repository, index, service


def proposal(service: MemoryV2Service, title: str = "Keep memory compact"):
    return service.propose(
        kind=MemoryKind.DECISION,
        title=title,
        body=f"{title} is a durable project decision.",
        source_commit="38183dd",
        tags=["memory", "v2"],
    )


def test_propose_is_native_v2_create_only_and_indexed(tmp_path: Path) -> None:
    repository, index, service = setup(tmp_path)

    created = proposal(service)

    assert created.envelope.schema_ == "trufagent.memory.v2"
    assert created.envelope.status == MemoryStateV2.PROPOSED
    assert created.envelope.governs_behavior is False
    assert Path(created.source_path).parent == repository.root
    assert index.search("compact", project="demo")[0].memory_id == created.envelope.id
    with pytest.raises(MemoryAlreadyExistsError, match="already exists"):
        proposal(service)


def test_accept_is_create_only_and_makes_memory_governing(tmp_path: Path) -> None:
    repository, _, service = setup(tmp_path)
    created = proposal(service)
    original = Path(created.source_path).read_text()

    accepted = service.accept(created.envelope.id, reviewer="user")

    assert accepted.envelope.status == MemoryStateV2.ACCEPTED
    assert accepted.envelope.governs_behavior is True
    assert Path(created.source_path).read_text() == original
    assert len(repository.events(created.envelope.id)) == 1


def test_replace_requires_an_accepted_replacement(tmp_path: Path) -> None:
    _, _, service = setup(tmp_path)
    old = proposal(service, "Old decision")
    replacement = proposal(service, "New decision")
    service.accept(old.envelope.id, reviewer="user")

    with pytest.raises(ValueError, match="replacement memory must be accepted"):
        service.replace(
            old.envelope.id,
            replacement_id=replacement.envelope.id,
            reviewer="user",
            reason="New evidence",
        )
    service.accept(replacement.envelope.id, reviewer="user")
    replaced = service.replace(
        old.envelope.id,
        replacement_id=replacement.envelope.id,
        reviewer="user",
        reason="New evidence",
    )

    assert replaced.envelope.status == MemoryStateV2.REPLACED


def test_retire_removes_memory_from_active_lifecycle(tmp_path: Path) -> None:
    _, index, service = setup(tmp_path)
    created = proposal(service)

    retired = service.retire(created.envelope.id, reviewer="user", reason="No longer applicable")

    assert retired.envelope.status == MemoryStateV2.RETIRED
    assert index.search("compact", project="demo") == []
    with pytest.raises(ValueError, match="active memory"):
        service.retire(created.envelope.id, reviewer="user", reason="Again")


def test_native_search_returns_only_relevant_active_memory(tmp_path: Path) -> None:
    repository, _, service = setup(tmp_path)
    active = proposal(service, "Active checklist decision")
    retired = proposal(service, "Retired checklist decision")
    service.retire(retired.envelope.id, reviewer="user", reason="No longer applicable")

    found = repository.search("checklist", project="demo")

    assert [item.envelope.id for item in found] == [active.envelope.id]


def test_cli_propose_accept_and_retire_v2_memory(tmp_path: Path, capsys) -> None:
    document = tmp_path / "proposal.md"
    document.write_text(
        """---
schema: trufagent.memory.v2
id: mem_cli_v2_decision
kind: decision
title: Keep CLI memory compact
status: proposed
project: demo
created_at: 2026-08-01T01:00:00Z
updated_at: 2026-08-01T01:00:00Z
reviewed_by:
source_commit: 38183dd
tags: [memory]
---
The stable CLI uses the native v2 repository.
""",
        encoding="utf-8",
    )

    assert main(["memory", "propose", str(tmp_path), str(document), "--project", "demo"]) == 0
    proposed = json.loads(capsys.readouterr().out)
    assert proposed["memory_id"] == "mem_cli_v2_decision"

    assert (
        main(
            [
                "memory",
                "accept",
                str(tmp_path),
                "mem_cli_v2_decision",
                "--project",
                "demo",
                "--reviewer",
                "user",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["envelope"]["status"] == "accepted"

    assert (
        main(
            [
                "memory",
                "retire",
                str(tmp_path),
                "mem_cli_v2_decision",
                "--project",
                "demo",
                "--reviewer",
                "user",
                "--reason",
                "No longer current",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["envelope"]["status"] == "retired"
