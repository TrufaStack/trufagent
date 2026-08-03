import json
from pathlib import Path

from trufagent.application.evaluation import evaluate_suite, load_evaluation_suite
from trufagent.cli import main

ROOT = Path(__file__).parents[1]


def test_casebook_suite_has_all_twelve_real_cases() -> None:
    suite = load_evaluation_suite(ROOT / "evals" / "casebook.yaml")

    assert suite.name == "casebook-v1"
    assert [case.id for case in suite.cases] == [f"C{number:02}" for number in range(1, 13)]


def test_evaluation_reports_every_dimension_deterministically() -> None:
    suite = load_evaluation_suite(ROOT / "evals" / "casebook.yaml")

    first = evaluate_suite(suite)
    second = evaluate_suite(suite)

    assert first == second
    assert first.total == 12
    assert first.pass_rate == 1
    assert set(first.dimension_rates) == {
        "mode",
        "exploration",
        "execution",
        "verification",
        "autonomy",
        "ready",
        "skills",
        "evidence",
    }


def test_cli_emits_machine_readable_casebook_report(capsys) -> None:
    suite = ROOT / "evals" / "casebook.yaml"

    assert main(["eval", "casebook", str(suite), "--fail-under", "1"]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["suite"] == "casebook-v1"
    assert report["total"] == 12
