import json
from pathlib import Path

from trufagent.cli import main


def test_cartography_status_reports_missing_graph_as_structured_json(
    tmp_path: Path, capsys
) -> None:
    exit_code = main(["cartography", "status", str(tmp_path)])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["state"] == "missing_graph"
    assert output["graphify_version"] == "0.9.30"
    assert output["project_root"] == str(tmp_path)


def test_graph_is_canonical_and_cartography_remains_an_equivalent_alias(
    tmp_path: Path,
    capsys,
) -> None:
    graph_exit = main(["graph", "status", str(tmp_path)])
    graph_output = json.loads(capsys.readouterr().out)
    alias_exit = main(["cartography", "status", str(tmp_path)])
    alias_output = json.loads(capsys.readouterr().out)

    assert graph_exit == alias_exit == 0
    assert graph_output == alias_output
