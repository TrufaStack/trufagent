from __future__ import annotations

from pathlib import Path

from trufagent.application.errors import CartographyUnavailableError
from trufagent.application.plan_task import PlanTaskRequest, PlanTaskService
from trufagent.application.skill_catalog import InMemorySkillCatalog, SkillDescriptor
from trufagent.cli import main
from trufagent.domain.cartography import GraphQueryResult, GraphReference
from trufagent.domain.task import AutonomyBoundary, ModelTier, TaskKind, TaskSignals
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_markdown import load_memory_markdown

FIXTURES = Path(__file__).parent / "fixtures" / "memory"


class WorkingCartography:
    def query(self, project_root: Path, question: str, *, token_budget: int) -> GraphQueryResult:
        return GraphQueryResult(
            summary="NODE resolveChecklistJobType [src=src/api/save.ts loc=L10 community=API]",
            nodes=[
                GraphReference(
                    node_id="resolveChecklistJobType",
                    label="resolveChecklistJobType",
                    source_file="src/api/save.ts",
                )
            ],
            graphify_version="0.9.30",
            graph_commit="abc123",
        )


class BrokenCartography:
    def query(self, project_root: Path, question: str, *, token_budget: int) -> GraphQueryResult:
        raise CartographyUnavailableError("graph is stale")


def catalog() -> InMemorySkillCatalog:
    return InMemorySkillCatalog(
        [
            SkillDescriptor(
                name="systematic-debugging",
                source="github:obra/superpowers",
                version="4",
                reviewed=True,
            ),
            SkillDescriptor(
                name="brainstorming",
                source="github:obra/superpowers",
                version="4",
                reviewed=True,
            ),
            SkillDescriptor(
                name="unreviewed-helper",
                source="github:example/unknown",
                version="1",
                reviewed=False,
            ),
        ]
    )


def repository(tmp_path: Path) -> MarkdownMemoryRepository:
    memory = MarkdownMemoryRepository(tmp_path, project="jc-app")
    memory.initialize()
    memory.propose(load_memory_markdown(FIXTURES / "c02-checklist-risk.md"))
    return memory


def test_plan_task_composes_memory_graph_classification_and_minimum_skills(
    tmp_path: Path,
) -> None:
    service = PlanTaskService(
        repository(tmp_path),
        cartography=WorkingCartography(),
        skills=catalog(),
    )

    plan = service.plan(
        PlanTaskRequest(
            task="Diagnose disappearing checklist answers",
            project="jc-app",
            project_root=tmp_path,
            signals=TaskSignals(
                kind=TaskKind.BUG,
                cause_known=False,
                persistence=True,
                shared_contract=True,
            ),
        )
    )

    assert plan.strategy.skills == ["systematic-debugging"]
    assert plan.selected_skills[0].source == "github:obra/superpowers"
    assert plan.context.items[0].memory_id == "mem_C02_CHECKLIST_RISK"
    assert plan.context.cartography is not None
    assert plan.model_route.coordinator == ModelTier.NONE
    assert plan.coordinator_gate.disposition.value == "host-owned"
    assert "mem_C02_CHECKLIST_RISK" in plan.strategy.context.risks
    assert plan.strategy.context.structural_targets == ["resolveChecklistJobType"]
    assert "discovery-driven" in plan.summary


def test_missing_graph_degrades_trivial_task_but_blocks_impact_task(tmp_path: Path) -> None:
    service = PlanTaskService(
        repository(tmp_path),
        cartography=BrokenCartography(),
        skills=catalog(),
    )

    trivial = service.plan(
        PlanTaskRequest(
            task="Change a label",
            project="jc-app",
            project_root=tmp_path,
            signals=TaskSignals(kind=TaskKind.SMALL_CHANGE, solution_known=True),
        )
    )
    impact = service.plan(
        PlanTaskRequest(
            task="Change the known checklist persistence call",
            project="jc-app",
            project_root=tmp_path,
            signals=TaskSignals(
                kind=TaskKind.SMALL_CHANGE,
                solution_known=True,
                localized=True,
                persistence=True,
            ),
            required_symbols=["saveChecklist"],
        )
    )

    assert trivial.strategy.autonomy_boundary == AutonomyBoundary.PROCEED
    assert trivial.warnings == []
    assert impact.strategy.autonomy_boundary == AutonomyBoundary.BLOCK
    assert "refresh-cartography" in impact.strategy.evidence_required


def test_forced_skill_must_exist_and_be_reviewed_while_exclusions_win(tmp_path: Path) -> None:
    service = PlanTaskService(
        repository(tmp_path),
        cartography=WorkingCartography(),
        skills=catalog(),
    )

    plan = service.plan(
        PlanTaskRequest(
            task="Investigate bug",
            project="jc-app",
            project_root=tmp_path,
            signals=TaskSignals(kind=TaskKind.BUG, cause_known=False),
            use_skills=["unreviewed-helper", "missing-skill"],
            without_skills=["systematic-debugging"],
        )
    )

    assert plan.strategy.skills == []
    assert plan.selected_skills == []
    assert any("unreviewed-helper" in warning for warning in plan.warnings)
    assert any("missing-skill" in warning for warning in plan.warnings)


def test_missing_approved_artifact_remains_blocked_after_composition(tmp_path: Path) -> None:
    service = PlanTaskService(
        repository(tmp_path),
        cartography=WorkingCartography(),
        skills=catalog(),
    )

    plan = service.plan(
        PlanTaskRequest(
            task="Implement approved mobile navigation",
            project="jc-app",
            project_root=tmp_path,
            signals=TaskSignals(
                kind=TaskKind.FEATURE,
                solution_known=True,
                visual=True,
                approved_artifact=True,
                artifact_available=False,
            ),
        )
    )

    assert plan.strategy.autonomy_boundary == AutonomyBoundary.BLOCK
    assert "obtain-approved-artifact" in plan.strategy.evidence_required


def test_cli_builds_complete_plan_from_explicit_request(tmp_path: Path, capsys) -> None:
    request = tmp_path / "request.json"
    request.write_text(
        PlanTaskRequest(
            task="Change a local label",
            project="demo",
            project_root=tmp_path,
            signals=TaskSignals(kind=TaskKind.SMALL_CHANGE, solution_known=True),
        ).model_dump_json()
    )

    exit_code = main(["plan", "task", str(request)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"summary":"execution-driven; effort E=low/X=low/V=low' in output


def test_plan_skips_exploration_when_declared_graph_targets_are_complete(
    tmp_path: Path,
) -> None:
    class TargetCartography:
        def query(self, project_root, question, *, token_budget):
            del project_root, question, token_budget
            from trufagent.domain.cartography import (
                GraphQueryResult,
                GraphReference,
                GraphState,
            )

            return GraphQueryResult(
                summary="target complete",
                nodes=[
                    GraphReference(
                        node_id="saveChecklist",
                        label="saveChecklist()",
                        source_file="src/save.py",
                    ),
                    GraphReference(
                        node_id="saveChecklist-copy",
                        label="saveChecklist()",
                        source_file="src/other-save.py",
                    ),
                ],
                graphify_version="0.9.30",
                graph_state=GraphState.FRESH,
            )

    service = PlanTaskService(
        repository(tmp_path),
        cartography=TargetCartography(),
        skills=catalog(),
    )

    plan = service.plan(
        PlanTaskRequest(
            task="Update the known save call",
            project="jc-app",
            project_root=tmp_path,
            signals=TaskSignals(
                kind=TaskKind.SMALL_CHANGE,
                solution_known=True,
                localized=True,
            ),
            required_symbols=["saveChecklist"],
        )
    )

    assert plan.model_route.exploration == ModelTier.NONE
    assert plan.exploration_gate is not None
    assert plan.exploration_gate.disposition.value == "model-free"
    assert plan.strategy.context.structural_targets == ["saveChecklist()"]


def test_declared_symbols_are_included_in_graph_query(tmp_path: Path) -> None:
    class CapturingCartography:
        question = ""

        def query(self, project_root, question, *, token_budget):
            del project_root, token_budget
            self.question = question
            return GraphQueryResult(summary="", graphify_version="0.9.30")

    cartography = CapturingCartography()
    service = PlanTaskService(
        repository(tmp_path),
        cartography=cartography,
        skills=catalog(),
    )

    service.plan(
        PlanTaskRequest(
            task="Change the continuation documentation.",
            project="jc-app",
            project_root=tmp_path,
            signals=TaskSignals(
                kind=TaskKind.SMALL_CHANGE,
                solution_known=True,
                localized=True,
            ),
            required_symbols=["TaskPreviewRecord"],
        )
    )

    assert cartography.question == "TaskPreviewRecord"


def test_unknown_bug_cause_collects_cartography_without_skipping_model(
    tmp_path: Path,
) -> None:
    class CapturingCartography:
        called = False

        def query(self, project_root, question, *, token_budget):
            del project_root, token_budget
            self.called = True
            return GraphQueryResult(
                summary="target",
                nodes=[
                    GraphReference(
                        node_id=question,
                        label=f"{question}()",
                        source_file="lib/checklist-job-type.ts",
                    )
                ],
                graphify_version="0.9.30",
            )

    cartography = CapturingCartography()
    service = PlanTaskService(
        repository(tmp_path),
        cartography=cartography,
        skills=catalog(),
    )

    plan = service.plan(
        PlanTaskRequest(
            task="Diagnose why saved answers disappear silently.",
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

    assert cartography.called is True
    assert plan.context.cartography is not None
    assert plan.strategy.context.structural_targets == ["resolveChecklistJobType()"]
    assert plan.exploration_gate is not None
    assert plan.exploration_gate.disposition.value == "shadow-required"
    assert "bug cause is not confirmed" in plan.exploration_gate.reasons
