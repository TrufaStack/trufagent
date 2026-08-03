from pathlib import Path

from trufagent.application.plan_task import PlanTaskRequest, PlanTaskService
from trufagent.application.skill_catalog import InMemorySkillCatalog, SkillDescriptor
from trufagent.application.task_extractor import TaskIntake, extract_task_signals
from trufagent.domain.cartography import GraphQueryResult, GraphReference, GraphState
from trufagent.domain.task import ModelTier, TaskKind, TaskSignals
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_markdown import load_memory_markdown

FIXTURES = Path(__file__).parent / "fixtures" / "memory"


class KnownTargetCartography:
    def query(self, project_root, question, *, token_budget):
        del project_root, token_budget
        return GraphQueryResult(
            summary="known target",
            nodes=[
                GraphReference(
                    node_id=question,
                    label=f"{question}()",
                    source_file="src/known-target.ts",
                )
            ],
            graphify_version="0.9.30",
            graph_state=GraphState.FRESH,
        )


def repository(tmp_path: Path) -> MarkdownMemoryRepository:
    result = MarkdownMemoryRepository(tmp_path, project="jc-app").initialize()
    result.propose(load_memory_markdown(FIXTURES / "c02-checklist-risk.md"))
    return result


def catalog() -> InMemorySkillCatalog:
    return InMemorySkillCatalog(
        [
            SkillDescriptor(
                name=name,
                source="github:obra/superpowers",
                version="4",
                reviewed=True,
            )
            for name in ("systematic-debugging", "brainstorming")
        ]
    )


def test_small_known_change_uses_model_free_structural_shortcut(
    tmp_path: Path,
) -> None:
    plan = PlanTaskService(
        repository(tmp_path),
        cartography=KnownTargetCartography(),
        skills=catalog(),
    ).plan(
        PlanTaskRequest(
            task="Add a fixed temporary Schedule badge.",
            project="jc-app",
            project_root=tmp_path,
            signals=TaskSignals(
                kind=TaskKind.SMALL_CHANGE,
                solution_known=True,
                localized=True,
                multi_surface=True,
            ),
            required_symbols=["ScheduleView"],
        )
    )

    assert plan.model_route.exploration == ModelTier.NONE
    assert plan.model_route.execution == ModelTier.ECONOMY
    assert plan.model_route.verification == ModelTier.ECONOMY
    assert plan.strategy.context.structural_targets == ["ScheduleView()"]
    assert plan.strategy.evidence_required == ["all-surfaces-verified"]


def test_ambiguous_persistence_bug_uses_debugging_with_graph_context(
    tmp_path: Path,
) -> None:
    plan = PlanTaskService(
        repository(tmp_path),
        cartography=KnownTargetCartography(),
        skills=catalog(),
    ).plan(
        PlanTaskRequest(
            task="Diagnose why checklist persistence fails silently.",
            project="jc-app",
            project_root=tmp_path,
            signals=TaskSignals(
                kind=TaskKind.BUG,
                cause_known=False,
                persistence=True,
                silent_failure=True,
            ),
            required_symbols=["resolveChecklistJobType"],
        )
    )

    assert plan.context.cartography is not None
    assert plan.strategy.context.structural_targets == ["resolveChecklistJobType()"]
    assert [skill.name for skill in plan.selected_skills] == ["systematic-debugging"]
    assert plan.model_route.exploration == ModelTier.FRONTIER
    assert "mem_C02_CHECKLIST_RISK" in plan.strategy.context.risks
    assert "persistence-regression" in plan.strategy.evidence_required


def test_feature_with_unavailable_approved_artifact_stops_before_planning() -> None:
    extraction = extract_task_signals(
        TaskIntake(
            task=(
                "Implement the approved mockup for completed-stage navigation; "
                "the Artifact URL is not available."
            )
        )
    )

    assert extraction.ready_to_plan is False
    assert [question.field for question in extraction.questions] == ["artifact_available"]
    assert "obtain-approved-artifact" in extraction.strategy.evidence_required


def test_open_architecture_uses_brainstorming_consumer_audit_and_graph_context(
    tmp_path: Path,
) -> None:
    extraction = extract_task_signals(
        TaskIntake(
            task=(
                "Decide the architecture for checklist persistence and audit "
                "every consumer before implementation."
            )
        )
    )
    plan = PlanTaskService(
        repository(tmp_path),
        cartography=KnownTargetCartography(),
        skills=catalog(),
    ).plan(
        PlanTaskRequest(
            task=extraction.task,
            project="jc-app",
            project_root=tmp_path,
            signals=extraction.signals,
            required_symbols=["resolveChecklistJobType"],
        )
    )

    assert plan.context.cartography is not None
    assert [skill.name for skill in plan.selected_skills] == ["brainstorming"]
    assert "consumer-impact-search" in plan.strategy.evidence_required
    assert plan.model_route.exploration == ModelTier.FRONTIER
    assert "mem_C02_CHECKLIST_RISK" in plan.strategy.context.risks
