from __future__ import annotations

import json

import pytest

from trufagent.application.task_classifier import classify_task
from trufagent.cli import main
from trufagent.domain.task import (
    AutonomyBoundary,
    EffortLevel,
    TaskKind,
    TaskMode,
    TaskSignals,
)


@pytest.mark.parametrize(
    ("case_id", "signals", "mode", "budgets"),
    [
        (
            "C01",
            TaskSignals(kind=TaskKind.SMALL_CHANGE, solution_known=True),
            TaskMode.EXECUTION_DRIVEN,
            (EffortLevel.LOW, EffortLevel.LOW, EffortLevel.LOW),
        ),
        (
            "C02",
            TaskSignals(
                kind=TaskKind.BUG,
                cause_known=False,
                persistence=True,
                silent_failure=True,
                shared_contract=True,
            ),
            TaskMode.DISCOVERY_DRIVEN,
            (EffortLevel.HIGH, EffortLevel.MEDIUM, EffortLevel.HIGH),
        ),
        (
            "C03",
            TaskSignals(
                kind=TaskKind.FEATURE,
                open_decisions=True,
                permissions=True,
                multi_surface=True,
            ),
            TaskMode.MIXED,
            (EffortLevel.MEDIUM, EffortLevel.MEDIUM, EffortLevel.HIGH),
        ),
        (
            "C04",
            TaskSignals(
                kind=TaskKind.ARCHITECTURE,
                open_decisions=True,
                persistence=True,
                shared_contract=True,
            ),
            TaskMode.MIXED,
            (EffortLevel.HIGH, EffortLevel.MEDIUM, EffortLevel.HIGH),
        ),
        (
            "C05",
            TaskSignals(kind=TaskKind.DIAGNOSTIC, secrets=True, cause_known=False),
            TaskMode.DISCOVERY_DRIVEN,
            (EffortLevel.MEDIUM, EffortLevel.LOW, EffortLevel.CRITICAL),
        ),
        (
            "C06",
            TaskSignals(
                kind=TaskKind.BUG,
                cause_known=False,
                library_behavior=True,
                localized=True,
            ),
            TaskMode.MIXED,
            (EffortLevel.MEDIUM, EffortLevel.LOW, EffortLevel.MEDIUM),
        ),
        (
            "C07",
            TaskSignals(
                kind=TaskKind.BUG,
                cause_known=False,
                multi_surface=True,
                shared_symptom=True,
            ),
            TaskMode.DISCOVERY_DRIVEN,
            (EffortLevel.HIGH, EffortLevel.MEDIUM, EffortLevel.HIGH),
        ),
        (
            "C08",
            TaskSignals(
                kind=TaskKind.VISUAL_REDESIGN,
                solution_known=False,
                approved_artifact=True,
                multi_surface=True,
                library_behavior=True,
            ),
            TaskMode.DISCOVERY_DRIVEN,
            (EffortLevel.HIGH, EffortLevel.HIGH, EffortLevel.HIGH),
        ),
        (
            "C09",
            TaskSignals(
                kind=TaskKind.RESEARCH,
                hypothesis_may_negate_work=True,
                external_constraint=True,
            ),
            TaskMode.DISCOVERY_DRIVEN,
            (EffortLevel.HIGH, EffortLevel.NONE, EffortLevel.MEDIUM),
        ),
        (
            "C10",
            TaskSignals(
                kind=TaskKind.FEATURE,
                solution_known=True,
                approved_artifact=True,
                artifact_available=False,
                visual=True,
            ),
            TaskMode.EXECUTION_DRIVEN,
            (EffortLevel.HIGH, EffortLevel.MEDIUM, EffortLevel.HIGH),
        ),
        (
            "C11",
            TaskSignals(
                kind=TaskKind.PLANNED_IMPLEMENTATION,
                approved_plan=True,
                multi_surface=True,
                integration_testing=True,
            ),
            TaskMode.EXECUTION_DRIVEN,
            (EffortLevel.MEDIUM, EffortLevel.HIGH, EffortLevel.HIGH),
        ),
        (
            "C12",
            TaskSignals(
                kind=TaskKind.PLANNED_IMPLEMENTATION,
                approved_plan=True,
                solution_known=True,
                multi_surface=True,
                state_logic=True,
            ),
            TaskMode.EXECUTION_DRIVEN,
            (EffortLevel.LOW, EffortLevel.HIGH, EffortLevel.HIGH),
        ),
    ],
)
def test_casebook_acceptance_matrix(
    case_id: str,
    signals: TaskSignals,
    mode: TaskMode,
    budgets: tuple[EffortLevel, EffortLevel, EffortLevel],
) -> None:
    strategy = classify_task(signals)

    assert strategy.task_profile.mode == mode, case_id
    assert (
        strategy.budgets.exploration,
        strategy.budgets.execution,
        strategy.budgets.verification,
    ) == budgets, case_id
    assert strategy.reasons, case_id


def test_missing_approved_artifact_blocks_improvisation() -> None:
    strategy = classify_task(
        TaskSignals(
            kind=TaskKind.FEATURE,
            approved_artifact=True,
            artifact_available=False,
            visual=True,
        )
    )

    assert strategy.autonomy_boundary == AutonomyBoundary.BLOCK
    assert "obtain-approved-artifact" in strategy.evidence_required


def test_critical_risk_escalates_verification_without_inflating_execution() -> None:
    strategy = classify_task(
        TaskSignals(kind=TaskKind.SMALL_CHANGE, solution_known=True, secrets=True)
    )

    assert strategy.budgets.execution == EffortLevel.LOW
    assert strategy.budgets.verification == EffortLevel.CRITICAL
    assert strategy.autonomy_boundary == AutonomyBoundary.CONFIRM


def test_classifier_is_deterministic_and_explains_escalators() -> None:
    signals = TaskSignals(
        kind=TaskKind.BUG,
        cause_known=False,
        persistence=True,
        shared_contract=True,
    )

    first = classify_task(signals)
    second = classify_task(signals)

    assert first == second
    assert "unknown-cause" in first.reasons
    assert "persistence-risk" in first.reasons
    assert "shared-contract-impact" in first.reasons


def test_cli_classifies_a_signal_document(tmp_path, capsys) -> None:
    signals = tmp_path / "signals.json"
    signals.write_text(
        json.dumps(
            {
                "kind": "bug",
                "cause_known": False,
                "persistence": True,
                "shared_contract": True,
            }
        )
    )

    exit_code = main(["plan", "classify", str(signals)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["task_profile"]["mode"] == "discovery-driven"
    assert output["budgets"] == {
        "exploration": "high",
        "execution": "medium",
        "verification": "high",
    }
