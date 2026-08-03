from __future__ import annotations

from pathlib import Path

from trufagent.application.plan_task import PlanTaskService
from trufagent.application.prepare_task import PrepareTaskRequest, PrepareTaskService
from trufagent.application.prepare_v2 import project_prepare_v2
from trufagent.application.skill_catalog import InMemorySkillCatalog, SkillDescriptor
from trufagent.application.task_extractor import TaskIntake
from trufagent.domain.cartography import GraphQueryResult, GraphReference, GraphState
from trufagent.domain.prepare_v2 import Complexity, PhaseEffort, PrepareStatus
from trufagent.domain.task import ModelTier, TaskKind
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_markdown import load_memory_markdown

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
            )
            for name, reviewed in (
                ("systematic-debugging", True),
                ("brainstorming", True),
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
    assert result.task.kind == TaskKind.SMALL_CHANGE
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
        ("systematic-debugging", "bug cause is not yet demonstrated")
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

    assert [(skill.name, skill.reason) for skill in result.skills] == [
        ("tdd", "selected by task strategy or user override")
    ]


def test_v2_user_can_exclude_an_automatic_skill(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Diagnose why checklist persistence fails.",
        overrides={"kind": "bug", "cause_known": False},
        without_skills=["systematic-debugging"],
    )

    assert result.skills == []


def test_v2_context_exposes_memory_references_without_bodies(tmp_path: Path) -> None:
    result = _prepare(
        tmp_path,
        "Diagnose the checklist risk.",
        overrides={"kind": "bug", "cause_known": False},
    )

    assert result.context.memories
    assert result.context.memories[0].memory_id == "mem_C02_CHECKLIST_RISK"
    assert "body" not in result.model_dump(mode="json", by_alias=True)["context"]["memories"][0]


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

    assert result.skills == []
    assert any("not reviewed" in warning for warning in result.warnings)
    assert any("not installed" in warning for warning in result.warnings)
