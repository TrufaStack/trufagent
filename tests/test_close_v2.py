from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import trufagent.cli as cli_module
from trufagent.application.close_v2 import CloseV2Service
from trufagent.cli import main
from trufagent.domain.cartography import GraphState, GraphStatus
from trufagent.domain.close_v2 import CloseMemoryProposal, CloseV2Request
from trufagent.domain.memory import MemoryKind
from trufagent.infrastructure.git_merge import GitMergeVerifier
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_index import SqliteMemoryIndex
from trufagent.infrastructure.memory_v2_fs import MarkdownMemoryRepositoryV2

NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


class Merge:
    def __init__(self, merged: bool) -> None:
        self.merged = merged

    def contains(self, project_root: Path, commit: str, base_ref: str) -> bool:
        del project_root, commit, base_ref
        return self.merged


class Cartography:
    def __init__(self, state: GraphState) -> None:
        self.state = state

    def status(self, project_root: Path) -> GraphStatus:
        return GraphStatus(state=self.state, project_root=str(project_root))


class BrokenCartography:
    def status(self, project_root: Path) -> GraphStatus:
        del project_root
        raise ValueError("cartography unavailable")


def _request() -> CloseV2Request:
    return CloseV2Request(
        merged_commit="abcdef123456",
        summary="Added compact post-merge close.",
        verifications=["focused tests passed"],
        decisions=["V2 proposals remain human reviewed"],
        memory_proposals=[
            CloseMemoryProposal(
                kind=MemoryKind.DECISION,
                title="Keep close proposals reviewable",
                body="A close proposal cannot govern behavior before explicit acceptance.",
            )
        ],
    )


def test_close_rejects_unmerged_commit_before_writing(tmp_path: Path) -> None:
    memory = MarkdownMemoryRepository(tmp_path, project="demo").initialize()
    index_path = tmp_path / ".trufagent/memory-index.sqlite3"
    service = CloseV2Service(
        MarkdownMemoryRepositoryV2(tmp_path, project="demo").initialize(),
        memory,
        SqliteMemoryIndex(index_path),
        Merge(False),
        Cartography(GraphState.FRESH),
        project="demo",
        clock=lambda: NOW,
    )

    with pytest.raises(ValueError, match="is not merged"):
        service.close(tmp_path, _request())

    assert memory.documents() == []
    assert not index_path.exists()


def test_close_proposes_compatible_memory_and_rebuilds_index(tmp_path: Path) -> None:
    memory = MarkdownMemoryRepository(tmp_path, project="demo").initialize()
    index = SqliteMemoryIndex(tmp_path / ".trufagent/memory-index.sqlite3")
    v2_memory = MarkdownMemoryRepositoryV2(tmp_path, project="demo").initialize()
    result = CloseV2Service(
        v2_memory,
        memory,
        index,
        Merge(True),
        Cartography(GraphState.STALE_COMMIT),
        project="demo",
        clock=lambda: NOW,
    ).close(tmp_path, _request())

    proposed = v2_memory.read(result.proposed_memory_ids[0])
    assert result.schema_ == "trufagent.close.v2"
    assert result.indexed_memories == 1
    assert result.graph_update_required is True
    assert proposed.envelope.schema_ == "trufagent.memory.v2"
    assert proposed.envelope.status.value == "proposed"
    assert proposed.envelope.governs_behavior is False
    assert proposed.envelope.source_commit == "abcdef123456"
    assert index.search("reviewable", project="demo")


def test_close_checks_cartography_before_writing(tmp_path: Path) -> None:
    memory = MarkdownMemoryRepository(tmp_path, project="demo").initialize()
    index_path = tmp_path / ".trufagent/memory-index.sqlite3"
    service = CloseV2Service(
        MarkdownMemoryRepositoryV2(tmp_path, project="demo").initialize(),
        memory,
        SqliteMemoryIndex(index_path),
        Merge(True),
        BrokenCartography(),
        project="demo",
        clock=lambda: NOW,
    )

    with pytest.raises(ValueError, match="cartography unavailable"):
        service.close(tmp_path, _request())

    assert memory.documents() == []
    assert not index_path.exists()


def test_git_merge_verifier_uses_ancestor_exit_status(tmp_path: Path, monkeypatch) -> None:
    observed = []

    class Completed:
        returncode = 0
        stderr = ""

    def run(command, **kwargs):
        observed.append((command, kwargs))
        return Completed()

    monkeypatch.setattr("trufagent.infrastructure.git_merge.subprocess.run", run)

    assert GitMergeVerifier().contains(tmp_path, "abc1234", "main") is True
    assert observed[0][0] == ["git", "merge-base", "--is-ancestor", "abc1234", "main"]
    assert observed[0][1]["cwd"] == tmp_path.resolve()


def test_close_cli_emits_compact_v2_result(tmp_path: Path, monkeypatch, capsys) -> None:
    config = tmp_path / ".trufagent/config.yaml"
    config.parent.mkdir()
    config.write_text("schema: trufagent.project.v1\nproject: demo\n")
    request = tmp_path / "close.json"
    request.write_text(_request().model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(cli_module, "GitMergeVerifier", lambda: Merge(True))
    monkeypatch.setattr(
        cli_module, "GraphifyAdapter", lambda: Cartography(GraphState.FRESH)
    )

    assert main(["close", str(request), str(tmp_path)]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["schema"] == "trufagent.close.v2"
    assert output["status"] == "closed"
    assert output["graph_update_required"] is False
