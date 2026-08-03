from __future__ import annotations

import json

import pytest

from trufagent.application.plan_task import PlanTaskService
from trufagent.application.prepare_task import PrepareTaskRequest, PrepareTaskService
from trufagent.application.skill_catalog import InMemorySkillCatalog
from trufagent.application.task_extractor import (
    SignalSource,
    TaskIntake,
    extract_task_signals,
)
from trufagent.cli import main
from trufagent.domain.cartography import GraphQueryResult
from trufagent.domain.task import (
    AutonomyBoundary,
    EffortLevel,
    TaskKind,
    TaskMode,
)
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository


class EmptyCartography:
    def query(self, project_root, question: str, *, token_budget: int) -> GraphQueryResult:
        return GraphQueryResult(summary="", graphify_version="0.9.30")


def test_small_temporary_change_stays_small() -> None:
    result = extract_task_signals(
        TaskIntake(
            task=(
                'Agregar un badge temporal "Dianne fuera de oficina" en Schedule, '
                "con fechas fijas y visible solo para admins."
            )
        )
    )

    assert result.signals.kind == TaskKind.SMALL_CHANGE
    assert result.signals.localized is True
    assert result.signals.permissions is False
    assert result.strategy.budgets.exploration == EffortLevel.LOW
    assert result.ready_to_plan is True


def test_small_change_can_span_two_surfaces_without_becoming_high_effort() -> None:
    result = extract_task_signals(
        TaskIntake(
            task=(
                "Agregar un badge temporal en Schedule, en semana y mes, "
                "con tooltip y fechas fijas."
            )
        )
    )

    assert result.signals.multi_surface is True
    assert result.strategy.budgets.verification == EffortLevel.LOW
    assert "all-surfaces-verified" in result.strategy.evidence_required


def test_silent_persistence_bug_gets_discovery_signals() -> None:
    result = extract_task_signals(
        TaskIntake(
            task=(
                "Diagnose why checklist answers disappear after navigation and the user "
                "cannot advance. Saving shows no error."
            )
        )
    )

    assert result.signals.kind == TaskKind.BUG
    assert result.signals.cause_known is False
    assert result.signals.persistence is True
    assert result.signals.silent_failure is True
    assert result.signals.visual is False
    assert result.strategy.task_profile.mode == TaskMode.DISCOVERY_DRIVEN
    assert result.strategy.budgets.verification == EffortLevel.HIGH


def test_shared_symptom_across_surfaces_does_not_assume_shared_cause() -> None:
    result = extract_task_signals(
        TaskIntake(task="Attachments are not clickable in both Jobs and Archive; investigate why.")
    )

    assert result.signals.kind == TaskKind.BUG
    assert result.signals.multi_surface is True
    assert result.signals.shared_symptom is True
    assert result.signals.shared_contract is False


def test_missing_approved_artifact_creates_blocking_question() -> None:
    result = extract_task_signals(
        TaskIntake(task="Implement the approved Artifact design for the mobile bottom navigation.")
    )

    assert result.signals.approved_artifact is True
    assert result.signals.artifact_available is False
    assert result.ready_to_plan is False
    assert result.strategy.autonomy_boundary == AutonomyBoundary.BLOCK
    assert result.questions[0].field == "artifact_available"


def test_explicit_correction_wins_and_is_auditable() -> None:
    result = extract_task_signals(
        TaskIntake(
            task="Update the map control.",
            signal_overrides={
                "kind": "bug",
                "cause_known": True,
                "library_behavior": True,
                "localized": True,
            },
        )
    )

    assert result.signals.kind == TaskKind.BUG
    assert result.signals.cause_known is True
    corrected = {item.field: item for item in result.evidence if item.source == SignalSource.USER}
    assert set(corrected) == {"kind", "cause_known", "library_behavior", "localized"}


def test_extractor_is_deterministic_and_does_not_invent_risk() -> None:
    intake = TaskIntake(task="Change the text of the empty-state label.")

    first = extract_task_signals(intake)
    second = extract_task_signals(intake)

    assert first == second
    assert first.signals.secrets is False
    assert first.signals.production is False
    assert first.signals.persistence is False


def test_cli_extracts_signals_and_strategy(tmp_path, capsys) -> None:
    request = tmp_path / "intake.json"
    request.write_text(
        json.dumps(
            {
                "task": "Diagnose a password leak while checking environment variables.",
                "signal_overrides": {"kind": "diagnostic"},
            }
        )
    )

    assert main(["plan", "extract", str(request)]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["signals"]["secrets"] is True
    assert output["strategy"]["budgets"]["verification"] == "critical"
    assert output["strategy"]["autonomy_boundary"] == "confirm"


def test_every_consumer_requires_shared_contract_impact_search() -> None:
    result = extract_task_signals(
        TaskIntake(
            task=(
                "Decide the architecture and audit every persistence consumer "
                "before implementation."
            )
        )
    )

    assert result.signals.shared_contract is True
    assert "consumer-impact-search" in result.strategy.evidence_required


@pytest.mark.parametrize(
    ("case_id", "task", "kind", "true_fields"),
    [
        (
            "C03",
            "Permitir que electricistas naveguen stages completados de su propio "
            "field record en modo solo lectura.",
            TaskKind.FEATURE,
            {"permissions", "state_logic"},
        ),
        (
            "C04",
            "Decidir cómo un job genérico reutiliza un template bucket sin cambiar "
            "el tipo real; auditar todos los consumidores.",
            TaskKind.ARCHITECTURE,
            {"open_decisions", "shared_contract"},
        ),
        (
            "C05",
            "Run diagnostic commands for connectivity and environment variables "
            "without leaking the database password.",
            TaskKind.DIAGNOSTIC,
            {"secrets"},
        ),
        (
            "C06",
            "Fix MapLibre AttributionControl because the library reopens the control.",
            TaskKind.BUG,
            {"library_behavior", "localized"},
        ),
        (
            "C08",
            "Redesign the handover PDF from the approved mockup for three job types.",
            TaskKind.VISUAL_REDESIGN,
            {"visual", "approved_artifact"},
        ),
        (
            "C09",
            "Evaluate whether to build a cache/proxy for external GreenDeal attachments.",
            TaskKind.RESEARCH,
            {"hypothesis_may_negate_work", "external_constraint"},
        ),
        (
            "C11",
            "Implement the approved 12-step plan and verify it in integration preview.",
            TaskKind.PLANNED_IMPLEMENTATION,
            {"approved_plan", "integration_testing"},
        ),
        (
            "C12",
            "Execute the approved plan for job stage progress and state animation.",
            TaskKind.PLANNED_IMPLEMENTATION,
            {"approved_plan", "state_logic"},
        ),
    ],
)
def test_casebook_signal_extraction(
    case_id: str,
    task: str,
    kind: TaskKind,
    true_fields: set[str],
) -> None:
    result = extract_task_signals(TaskIntake(task=task))

    assert result.signals.kind == kind, case_id
    for field in true_fields:
        assert getattr(result.signals, field) is True, f"{case_id}:{field}"


def test_prepare_builds_plan_only_when_extraction_is_ready(tmp_path) -> None:
    repository = MarkdownMemoryRepository(tmp_path, project="demo").initialize()
    planner = PlanTaskService(
        repository,
        cartography=EmptyCartography(),
        skills=InMemorySkillCatalog([]),
    )
    service = PrepareTaskService(planner)

    ready = service.prepare(
        PrepareTaskRequest(
            intake=TaskIntake(task="Change the text of the empty-state label."),
            project="demo",
            project_root=tmp_path,
        )
    )
    blocked = service.prepare(
        PrepareTaskRequest(
            intake=TaskIntake(task="Implement the approved Artifact design for mobile navigation."),
            project="demo",
            project_root=tmp_path,
        )
    )

    assert ready.plan is not None
    assert ready.plan.strategy.budgets.execution == EffortLevel.LOW
    assert blocked.plan is None
    assert blocked.extraction.questions[0].field == "artifact_available"


def test_cli_prepare_hands_ready_signals_to_plan_task(tmp_path, capsys) -> None:
    intake = tmp_path / "intake.json"
    intake.write_text(json.dumps({"task": "Change the text of the empty-state label."}))

    assert main(["plan", "prepare", str(intake), str(tmp_path), "--project", "demo"]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["extraction"]["ready_to_plan"] is True
    assert output["plan"]["strategy"]["budgets"]["execution"] == "low"
