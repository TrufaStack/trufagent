from __future__ import annotations

import json
from pathlib import Path

import pytest

import trufagent.cli as cli_module
from trufagent.cli import main
from trufagent.domain.cartography import GraphQueryResult, GraphReference, GraphState
from trufagent.infrastructure.skill_catalog_fs import SkillCatalogRepository
from trufagent.infrastructure.skill_discovery import SkillDiscovery


class MatrixCartography:
    calls: list[str] = []

    def query(self, project_root: Path, question: str, *, token_budget: int):
        del project_root, token_budget
        self.calls.append(question)
        return GraphQueryResult(
            summary="controlled structural context",
            nodes=[
                GraphReference(
                    node_id="TaskRouter",
                    label="TaskRouter",
                    source_file="src/trufagent/application/task_classifier_v2.py",
                )
            ],
            graphify_version="test",
            graph_state=GraphState.FRESH,
        )


def _write_skill(root: Path, name: str) -> None:
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"---\nname: {name}\ndescription: Controlled matrix skill for {name}\n---\n# Use\n",
        encoding="utf-8",
    )


def _catalog(tmp_path: Path) -> Path:
    root = tmp_path / "skills"
    for name in (
        "systematic-debugging",
        "brainstorming",
        "implement-with-evidence",
        "review-and-remember",
    ):
        _write_skill(root, name)
    catalog = SkillDiscovery({"codex": root}).scan().catalog
    for entry in catalog.entries:
        entry.reviewed = True
    path = tmp_path / "catalog.yaml"
    SkillCatalogRepository(path).save(catalog)
    return path


@pytest.mark.parametrize(
    ("task", "overrides", "kind", "complexity", "tier", "skills", "phases", "graph"),
    [
        (
            "Change one fixed label.",
            {"kind": "small-change", "solution_known": True, "localized": True},
            "small-change",
            "low",
            "economy",
            [],
            [],
            False,
        ),
        (
            "Fix the known label parsing defect.",
            {"kind": "bug", "cause_known": True, "localized": True},
            "fix",
            "low",
            "economy",
            ["implement-with-evidence", "review-and-remember"],
            ["implement", "verify"],
            False,
        ),
        (
            "Diagnose disappearing persisted values.",
            {"kind": "bug", "cause_known": False, "persistence": True},
            "fix",
            "high",
            "frontier",
            ["systematic-debugging", "implement-with-evidence", "review-and-remember"],
            ["explore", "implement", "verify"],
            True,
        ),
        (
            "Add filtering to the checklist.",
            {"kind": "feature", "solution_known": True},
            "feature",
            "medium",
            "balanced",
            ["implement-with-evidence", "review-and-remember"],
            ["implement", "verify"],
            False,
        ),
        (
            "Choose a persistence architecture.",
            {"kind": "architecture", "open_decisions": True},
            "architecture",
            "high",
            "frontier",
            ["brainstorming"],
            ["explore"],
            True,
        ),
        (
            "Research alternatives for persistence.",
            {"kind": "research"},
            "research",
            "high",
            "frontier",
            [],
            [],
            True,
        ),
    ],
)
def test_prepare_cli_routing_matrix(
    tmp_path: Path,
    monkeypatch,
    capsys,
    task,
    overrides,
    kind,
    complexity,
    tier,
    skills,
    phases,
    graph,
) -> None:
    MatrixCartography.calls = []
    monkeypatch.setattr(cli_module, "GraphifyAdapter", MatrixCartography)
    catalog = _catalog(tmp_path)
    intake = tmp_path / "intake.json"
    intake.write_text(json.dumps({"task": task, "signal_overrides": overrides}), encoding="utf-8")

    exit_code = main(
        [
            "prepare",
            str(intake),
            str(tmp_path),
            "--project",
            "matrix",
            "--catalog",
            str(catalog),
            "--harness",
            "codex",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["task"] == {"kind": kind, "complexity": complexity}
    assert output["model_tier"] == tier
    assert [skill["name"] for skill in output["skills"]] == skills
    assert [skill["phase"] for skill in output["skills"]] == phases
    assert bool(output["context"]["graph"]) is graph
    assert bool(MatrixCartography.calls) is graph
