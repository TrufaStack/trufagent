from __future__ import annotations

import json
from pathlib import Path

import pytest

from trufagent.domain.cartography import GraphState
from trufagent.infrastructure.graphify_adapter import (
    CommandResult,
    GraphifyAdapter,
    GraphifyCommandError,
)


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], CommandResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[tuple[str, ...], Path]] = []

    def __call__(self, command: list[str], *, cwd: Path, timeout: int) -> CommandResult:
        key = tuple(command)
        self.calls.append((key, cwd))
        return self.responses.get(key, CommandResult(0, "", ""))


def write_graph(
    root: Path,
    *,
    commit: str = "abc123",
    nodes: list[dict[str, str]] | None = None,
) -> Path:
    graph = root / "graphify-out" / "graph.json"
    graph.parent.mkdir(parents=True, exist_ok=True)
    graph.write_text(
        json.dumps(
            {
                "directed": True,
                "multigraph": False,
                "built_at_commit": commit,
                "nodes": nodes if nodes is not None else [{"id": "n1", "label": "save"}],
                "links": [],
            }
        )
    )
    return graph


def adapter(root: Path, runner: FakeRunner) -> GraphifyAdapter:
    return GraphifyAdapter(
        command=["python", "-m", "graphify"],
        runner=runner,
        version_provider=lambda: "0.9.30",
    )


def test_status_distinguishes_missing_corrupt_stale_dirty_and_fresh(tmp_path: Path) -> None:
    runner = FakeRunner(
        {
            ("git", "rev-parse", "HEAD"): CommandResult(0, "abc123\n", ""),
            ("git", "status", "--porcelain"): CommandResult(0, "", ""),
        }
    )
    graphify = adapter(tmp_path, runner)
    assert graphify.status(tmp_path).state == GraphState.MISSING_GRAPH

    graph = write_graph(tmp_path)
    graph.write_text("{broken")
    assert graphify.status(tmp_path).state == GraphState.CORRUPT

    write_graph(tmp_path, commit="old")
    assert graphify.status(tmp_path).state == GraphState.STALE_COMMIT

    write_graph(tmp_path)
    runner.responses[("git", "status", "--porcelain")] = CommandResult(0, " M app.py\n", "")
    assert graphify.status(tmp_path).state == GraphState.DIRTY_WORKTREE

    runner.responses[("git", "status", "--porcelain")] = CommandResult(0, "", "")
    assert graphify.status(tmp_path).state == GraphState.FRESH


def test_empty_graph_is_incomplete(tmp_path: Path) -> None:
    runner = FakeRunner(
        {
            ("git", "rev-parse", "HEAD"): CommandResult(0, "abc123\n", ""),
            ("git", "status", "--porcelain"): CommandResult(0, "", ""),
        }
    )
    write_graph(tmp_path, nodes=[])

    assert adapter(tmp_path, runner).status(tmp_path).state == GraphState.INCOMPLETE


def test_query_passes_budget_and_parses_nodes_and_edges(tmp_path: Path) -> None:
    graph = write_graph(tmp_path)
    output = (
        "NODE saveChecklist [src=src/save.py loc=10 community=Persistence]\n"
        "NODE Job [src=src/models.py loc=4 community=Domain]\n"
        "EDGE saveChecklist --writes [AST]--> Job at=src/save.py:12"
    )
    command = (
        "python",
        "-m",
        "graphify",
        "query",
        "where is checklist saved?",
        "--budget",
        "321",
        "--graph",
        str(graph),
    )
    runner = FakeRunner({command: CommandResult(0, output, "")})

    result = adapter(tmp_path, runner).query(
        tmp_path, "where is checklist saved?", token_budget=321
    )

    assert [node.label for node in result.nodes] == ["saveChecklist", "Job"]
    assert result.nodes[0].source_file == "src/save.py"
    assert result.edges == ["saveChecklist --writes [AST]--> Job at=src/save.py:12"]
    assert runner.calls[-1][0] == command


def test_affected_repeats_relation_flags_without_shell(tmp_path: Path) -> None:
    graph = write_graph(tmp_path)
    command = (
        "python",
        "-m",
        "graphify",
        "affected",
        "saveChecklist",
        "--relation",
        "calls",
        "--relation",
        "imports",
        "--depth",
        "3",
        "--graph",
        str(graph),
    )
    runner = FakeRunner({command: CommandResult(0, "Affected nodes for saveChecklist", "")})

    adapter(tmp_path, runner).affected(
        tmp_path, "saveChecklist", relations=["calls", "imports"], depth=3
    )

    assert runner.calls[-1][0] == command


def test_update_records_derived_manifest_and_surfaces_command_failure(tmp_path: Path) -> None:
    update = ("python", "-m", "graphify", "update", str(tmp_path))
    runner = FakeRunner({update: CommandResult(1, "", "extraction failed")})
    graphify = adapter(tmp_path, runner)

    with pytest.raises(GraphifyCommandError, match="extraction failed"):
        graphify.update(tmp_path)

    write_graph(tmp_path)
    runner.responses[update] = CommandResult(0, "updated", "")
    runner.responses[("git", "rev-parse", "HEAD")] = CommandResult(0, "abc123\n", "")
    runner.responses[("git", "status", "--porcelain")] = CommandResult(0, "", "")

    status = graphify.update(tmp_path)
    manifest = json.loads((tmp_path / ".trufagent/cartography/manifest.json").read_text())

    assert status.state == GraphState.FRESH
    assert manifest["graphify_version"] == "0.9.30"
    assert manifest["graph_path"] == str(tmp_path / "graphify-out/graph.json")
