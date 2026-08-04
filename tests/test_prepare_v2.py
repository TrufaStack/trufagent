from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from trufagent.application.plan_task import PlanTaskService
from trufagent.application.prepare_task import PrepareTaskRequest, PrepareTaskService
from trufagent.application.prepare_v2 import project_prepare_v2
from trufagent.application.skill_catalog import InMemorySkillCatalog, SkillDescriptor
from trufagent.application.task_extractor import TaskIntake
from trufagent.cli import main
from trufagent.domain.cartography import GraphQueryResult, GraphReference, GraphState
from trufagent.domain.memory import MemoryKind
from trufagent.domain.memory_v2 import MemoryDocumentV2, MemoryEnvelopeV2, MemoryStateV2
from trufagent.domain.prepare_v2 import Complexity, PhaseEffort, PrepareStatus, SkillPhase
from trufagent.domain.skills import SkillLocation
from trufagent.domain.task import ModelTier
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_markdown import load_memory_markdown
from trufagent.infrastructure.memory_v2_fs import MarkdownMemoryRepositoryV2

FIXTURES = Path(__file__).parent / "fixtures" / "memory"


class V2Cartography:
    def query(self, project_root, question, *, token_budget):
        del project_root, token_budget
        return GraphQueryResult(
            summary="known structural target",
            nodes=[
                GraphReference(
                    node_id=question,
                    label=f"{question}()",
                    source_file="src/checklist.py",
                )
            ],
            graphify_version="0.9.32",
            graph_state=GraphState.FRESH,
        )


def _catalog() -> InMemorySkillCatalog:
    return InMemorySkillCatalog(
        [
            SkillDescriptor(
                name=name,
                source="test",
                version="1",
                reviewed=reviewed,
                locations=[SkillLocation(platform="codex", path=f"/skills/{name}/SKILL.md")],
            )
            for name, reviewed in (
                ("systematic-debugging", True),
                ("brainstorming", True),
                ("implement-with-evidence", True),
                ("review-and-remember", True),
                ("tdd", True),
                ("unreviewed-helper", False),
            )
        ]
    )


def _service(tmp_path: Path) -> PrepareTaskService:
    repository = MarkdownMemoryRepository(tmp_path, project="jc-app").initialize()
    repository.propose(load_memory_markdown(FIXTURES / "c02-checklist-risk.md"))
    planner = PlanTaskService(
        repository,
        cartography=V2Cartography(),
        skills=_catalog(),
    )
    return PrepareTaskService(planner)


def _prepare(
    tmp_path: Path,
    task: str,
    *,
    overrides: dict | None = None,
    required_symbols: list[str] | None = None,
    use_skills: list[str] | None = None,
    without_skills: list[str] | None = None,
):
    prepared = _service(tmp_path).prepare(
        PrepareTaskRequest(
            intake=TaskIntake(
                task=task,
                signal_overrides=overrides or {},
                required_symbols=required_symbols or [],
            ),
            project="jc-app",
            project_root=tmp_path,
            use_skills=use_skills or [],
            without_skills=without_skills or [],
        )
    )
    return project_prepare_v2(prepared)


def test_v2_contract_has_a_stable_schema_identifier(tmp_path: Path) -> None:
    result = _prepare(tmp_path, "Change one fixed label.")

    payload = result.model_dump(mode="json", by_alias=True)

    assert payload["schema"] == "trufagent.prepare.v2"
    assert payload["status"] == "ready"


def test_v2_small_change_is_low_complexity_and_economy(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Change one fixed label.",
        overrides={"kind": "small-change", "solution_known": True, "localized": True},
    )

    assert result.task is not None
    assert result.task.kind == "small-change"
    assert result.task.complexity == Complexity.LOW
    assert result.model_tier == ModelTier.ECONOMY
    assert result.skills == []


def test_v2_unknown_bug_selects_debugging_and_high_exploration(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Diagnose why checklist persistence fails silently.",
        overrides={"kind": "bug", "cause_known": False, "persistence": True},
    )

    assert result.task is not None
    assert result.task.complexity == Complexity.HIGH
    assert result.model_tier == ModelTier.FRONTIER
    assert result.effort is not None
    assert result.effort.explore == PhaseEffort.HIGH
    assert [(skill.name, skill.reason) for skill in result.skills] == [
        ("systematic-debugging", "fix cause is not yet demonstrated"),
        (
            "implement-with-evidence",
            "behavior change requires proportionate implementation proof",
        ),
        (
            "review-and-remember",
            "completed change requires review and durable-memory triage",
        ),
    ]
    assert [skill.phase for skill in result.skills] == [
        SkillPhase.EXPLORE,
        SkillPhase.IMPLEMENT,
        SkillPhase.VERIFY,
    ]


def test_v2_normal_feature_is_balanced(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Add checklist filtering.",
        overrides={"kind": "feature", "solution_known": True},
    )

    assert result.task is not None
    assert result.task.complexity == Complexity.MEDIUM
    assert result.model_tier == ModelTier.BALANCED
    assert result.effort is not None
    assert result.effort.implement == PhaseEffort.MEDIUM
    assert [skill.name for skill in result.skills] == [
        "implement-with-evidence",
        "review-and-remember",
    ]


def test_v2_open_architecture_selects_brainstorming(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Decide the architecture for checklist persistence.",
        overrides={"kind": "architecture", "open_decisions": True},
    )

    assert result.task is not None
    assert result.task.complexity == Complexity.HIGH
    assert result.model_tier == ModelTier.FRONTIER
    assert [(skill.name, skill.reason) for skill in result.skills] == [
        ("brainstorming", "task contains open decisions")
    ]


def test_v2_user_can_force_a_reviewed_skill(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Add checklist filtering.",
        overrides={"kind": "feature", "solution_known": True},
        use_skills=["tdd"],
    )

    assert [skill.name for skill in result.skills] == [
        "implement-with-evidence",
        "review-and-remember",
        "tdd",
    ]
    assert result.skills[-1].reason == "selected by user override"
    assert result.skills[-1].phase == SkillPhase.ANY
    assert result.skills[-1].location == "/skills/tdd/SKILL.md"


def test_v2_user_can_exclude_an_automatic_skill(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Diagnose why checklist persistence fails.",
        overrides={"kind": "bug", "cause_known": False},
        without_skills=["systematic-debugging"],
    )

    assert [skill.name for skill in result.skills] == [
        "implement-with-evidence",
        "review-and-remember",
    ]


def test_v2_context_exposes_memory_references_without_bodies(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Diagnose the checklist risk.",
        overrides={"kind": "bug", "cause_known": False},
    )

    assert result.context.memories
    assert result.context.memories[0].memory_id == "mem_C02_CHECKLIST_RISK"
    assert "body" not in result.model_dump(mode="json", by_alias=True)["context"]["memories"][0]


def test_cli_prepare_combines_active_v1_and_v2_memory_with_provenance(
    tmp_path: Path,
    capsys,
) -> None:
    config = tmp_path / ".trufagent/config.yaml"
    config.parent.mkdir()
    config.write_text("schema: trufagent.project.v1\nproject: jc-app\n")
    legacy = MarkdownMemoryRepository(tmp_path, project="jc-app").initialize()
    legacy.propose(load_memory_markdown(FIXTURES / "c02-checklist-risk.md"))
    now = datetime(2026, 8, 4, tzinfo=UTC)
    native = MarkdownMemoryRepositoryV2(tmp_path, project="jc-app").initialize()
    native.propose(
        MemoryDocumentV2(
            envelope=MemoryEnvelopeV2(
                schema="trufagent.memory.v2",
                id="mem_native_checklist",
                kind=MemoryKind.DECISION,
                title="Keep native checklist context",
                status=MemoryStateV2.PROPOSED,
                project="jc-app",
                created_at=now,
                updated_at=now,
                source_commit="abcdef123456",
            ),
            body="Checklist retrieval must include native v2 context.",
        )
    )
    intake = tmp_path / "intake.json"
    intake.write_text(json.dumps({"task": "Diagnose checklist retrieval."}))

    exit_code = main(["prepare", str(intake), str(tmp_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    memories = {item["memory_id"]: item for item in output["context"]["memories"]}
    assert set(memories) == {"mem_C02_CHECKLIST_RISK", "mem_native_checklist"}
    assert memories["mem_C02_CHECKLIST_RISK"]["memory_schema"] == "trufagent.memory.v1"
    assert memories["mem_native_checklist"]["memory_schema"] == "trufagent.memory.v2"
    assert memories["mem_native_checklist"]["source_commit"] == "abcdef123456"


def test_v2_context_exposes_traceable_graph_references(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Change checklist persistence.",
        overrides={"kind": "feature", "solution_known": True},
        required_symbols=["ChecklistService"],
    )

    assert [(item.label, item.source_file) for item in result.context.graph] == [
        ("ChecklistService()", "src/checklist.py")
    ]


def test_v2_needs_input_does_not_emit_an_execution_plan(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Implement the approved Artifact design; the Artifact URL is unavailable.",
    )

    assert result.status == PrepareStatus.NEEDS_INPUT
    assert result.task is None
    assert result.model_tier is None
    assert result.effort is None
    assert [question.field for question in result.questions] == ["artifact_available"]


def test_v2_surfaces_unavailable_or_unreviewed_skill_warnings(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Add checklist filtering.",
        overrides={"kind": "feature", "solution_known": True},
        use_skills=["unreviewed-helper", "missing-helper"],
    )

    assert [skill.name for skill in result.skills] == [
        "implement-with-evidence",
        "review-and-remember",
    ]
    assert any("not reviewed" in warning for warning in result.warnings)
    assert any("not installed" in warning for warning in result.warnings)


def test_cli_prepare_emits_the_compact_v2_contract(tmp_path: Path, capsys) -> None:
    intake = tmp_path / "intake.json"
    intake.write_text(
        json.dumps(
            {
                "task": "Change one fixed label.",
                "signal_overrides": {
                    "kind": "small-change",
                    "solution_known": True,
                    "localized": True,
                },
            }
        )
    )

    exit_code = main(["prepare", str(intake), str(tmp_path), "--project", "demo"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["schema"] == "trufagent.prepare.v2"
    assert output["status"] == "ready"
    assert output["task"] == {"kind": "small-change", "complexity": "low"}
    assert output["model_tier"] == "economy"
    assert "plan" not in output
    assert "extraction" not in output


def test_cli_prepare_surfaces_only_questions_when_input_is_missing(
    tmp_path: Path,
    capsys,
) -> None:
    intake = tmp_path / "intake.json"
    intake.write_text(
        json.dumps({"task": "Implement the approved Artifact design; its URL is unavailable."})
    )

    exit_code = main(["prepare", str(intake), str(tmp_path), "--project", "demo"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["status"] == "needs_input"
    assert [question["field"] for question in output["questions"]] == ["artifact_available"]
    assert output["task"] is None
