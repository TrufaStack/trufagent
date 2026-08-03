import json

from trufagent.cli import main


def test_promotion_cli_initializes_policy_and_reports_honest_blockers(
    tmp_path,
    capsys,
) -> None:
    assert main(["promotion", "init", str(tmp_path)]) == 0
    initialized = json.loads(capsys.readouterr().out)
    assert initialized["status"] == "success"

    assert main(["promotion", "status", str(tmp_path)]) == 1
    status = json.loads(capsys.readouterr().out)
    assert status["schema"] == "trufagent.promotion-readiness.v1"
    assert status["status"] == "blocked"
    assert status["ready"] is False
    assert status["checks"]["sanitized-context-projection"] is True
    assert "sanitized-context-projection" not in status["missing"]


def test_promotion_cli_prepares_isolated_workspace(tmp_path, capsys) -> None:
    (tmp_path / "app.py").write_text("VALUE = 1\n")
    assert main(["promotion", "init", str(tmp_path)]) == 0
    capsys.readouterr()

    assert main(["promotion", "workspace", str(tmp_path)]) == 0
    workspace = json.loads(capsys.readouterr().out)

    assert workspace["source_write_allowed"] is False
    assert workspace["apply_allowed"] is False
    assert workspace["workspace_root"] != str(tmp_path)
