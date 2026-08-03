import json
import shlex

from trufagent.cli import main


def test_personal_task_builds_compact_preview_without_intake_file(
    tmp_path,
    capsys,
) -> None:
    project_root = tmp_path / "project with spaces"
    result = main(
        [
            "task",
            "Agregar un badge temporal con fechas fijas.",
            "--root",
            str(project_root),
            "--project",
            "demo",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["schema"] == "trufagent.task-preview.v1"
    assert output["status"] == "ready"
    assert output["signals"]["kind"] == "small-change"
    assert output["route"]["execution"] == "economy"
    assert output["exploration_gate"] is None
    assert output["session_id"].startswith("ses_")
    assert output["preview_id"].startswith("tp_")
    assert output["continuations"]["local"].endswith("--mode local")
    assert (
        f"--root {shlex.quote(str(project_root))}"
        in output["continuations"]["local"]
    )
    assert "context" not in output
    session_state = (
        project_root / ".trufagent" / "state" / "current-session.yaml"
    ).read_text()
    assert "Agregar un badge" not in session_state
    assert "Personal task " in session_state
    preview_state = next(
        (project_root / ".trufagent" / "state" / "task-previews").glob("*.json")
    ).read_text()
    assert "Agregar un badge" not in preview_state


def test_personal_task_surfaces_blocking_question_instead_of_planning(
    tmp_path,
    capsys,
) -> None:
    result = main(
        [
            "task",
            "Implementar el mockup aprobado para la navegación mobile.",
            "--root",
            str(tmp_path),
            "--project",
            "demo",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert result == 2
    assert output["status"] == "needs-input"
    assert output["questions"][0]["field"] == "artifact_available"
    assert "route" not in output


def test_personal_task_correction_is_visible_and_wins(
    tmp_path,
    capsys,
) -> None:
    result = main(
        [
            "task",
            "Update the map control.",
            "--root",
            str(tmp_path),
            "--project",
            "demo",
            "--kind",
            "bug",
            "--cause-known",
            "--localized",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["signals"]["kind"] == "bug"
    assert output["signals"]["cause_known"] is True
    corrected = {item["field"]: item for item in output["inferences"] if item["source"] == "user"}
    assert set(corrected) == {"kind", "cause_known", "localized"}


def test_local_continuation_requires_confirmation_then_returns_safe_handoff(
    tmp_path,
    capsys,
) -> None:
    assert (
        main(
            [
                "task",
                "Agregar un badge temporal con fechas fijas.",
                "--root",
                str(tmp_path),
                "--project",
                "demo",
            ]
        )
        == 0
    )
    preview = json.loads(capsys.readouterr().out)
    base = [
        "task-continue",
        preview["preview_id"],
        "--root",
        str(tmp_path),
        "--mode",
        "local",
    ]

    assert main(base) == 2
    confirmation = json.loads(capsys.readouterr().out)
    assert confirmation["status"] == "confirmation-required"

    assert main([*base, "--confirm"]) == 0
    handoff = json.loads(capsys.readouterr().out)
    assert handoff["schema"] == "trufagent.local-handoff.v1"
    assert handoff["status"] == "ready"
    assert "task" not in handoff


def test_shadow_continuation_verifies_task_digest(
    tmp_path,
    capsys,
) -> None:
    task = "Diagnose why saved answers disappear and no error is shown."
    assert (
        main(
            [
                "task",
                task,
                "--root",
                str(tmp_path),
                "--project",
                "demo",
            ]
        )
        == 0
    )
    preview = json.loads(capsys.readouterr().out)

    result = main(
        [
            "task-continue",
            preview["preview_id"],
            "--root",
            str(tmp_path),
            "--mode",
            "shadow",
            "--task-text",
            "Different task",
            "--confirm",
        ]
    )

    assert result == 1
    error = json.loads(capsys.readouterr().err)
    assert "does not match" in error["summary"]


def test_shadow_continuation_preserves_declared_symbols_when_graph_abstains(
    tmp_path,
    capsys,
) -> None:
    task = "Diagnose why saved answers disappear and no error is shown."
    assert (
        main(
            [
                "task",
                task,
                "--root",
                str(tmp_path),
                "--project",
                "demo",
                "--kind",
                "bug",
                "--no-cause-known",
                "--required-symbol",
                "resolveChecklistJobType",
            ]
        )
        == 0
    )
    preview = json.loads(capsys.readouterr().out)
    assert preview["required_symbols"] == ["resolveChecklistJobType"]
    assert preview["structural_targets"] == []

    assert (
        main(
            [
                "task-continue",
                preview["preview_id"],
                "--root",
                str(tmp_path),
                "--mode",
                "shadow",
                "--task-text",
                task,
                "--confirm",
            ]
        )
        == 0
    )
    authorization = json.loads(capsys.readouterr().out)
    assert authorization["status"] == "authorization-required"
    assert authorization["required_symbols"] == ["resolveChecklistJobType"]
    assert authorization["model_tier"] == "frontier"
    invocation = authorization["shadow_invocation"]
    assert invocation["preview"] == preview["preview_id"]
    assert invocation["inherits"] == [
        "signals",
        "required_symbols",
        "model_tier",
    ]
    assert "--confirm-provider" in invocation["required_flags"]
    assert task not in json.dumps(invocation)
