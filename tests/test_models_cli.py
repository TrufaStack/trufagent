from __future__ import annotations

import json
from pathlib import Path

from trufagent.cli import main


def test_cli_resolves_default_and_project_model_profiles(tmp_path: Path, capsys) -> None:
    assert (
        main(
            [
                "models",
                "resolve",
                str(tmp_path),
                "--harness",
                "codex",
                "--tier",
                "economy",
            ]
        )
        == 0
    )
    default = json.loads(capsys.readouterr().out)
    assert default["model"] == "gpt-5.6-luna"
    assert default["reasoning_effort"] == "max"
    assert default["source"] == "default"

    config = tmp_path / ".trufagent" / "config.yaml"
    config.parent.mkdir()
    config.write_text("models:\n  codex:\n    economy: local-model\n")

    assert (
        main(
            [
                "models",
                "resolve",
                str(tmp_path),
                "--harness",
                "codex",
                "--tier",
                "economy",
            ]
        )
        == 0
    )
    overridden = json.loads(capsys.readouterr().out)
    assert overridden["model"] == "local-model"
    assert overridden["reasoning_effort"] == "max"
    assert overridden["source"] == "project"
