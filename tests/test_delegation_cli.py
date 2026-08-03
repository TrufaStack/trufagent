from __future__ import annotations

import json
from pathlib import Path

from trufagent.cli import main
from trufagent.domain.delegation import DelegationPhase, UsageRecord
from trufagent.domain.task import Harness


def test_cli_compiles_protocol_without_invoking_models(tmp_path: Path, capsys) -> None:
    request = tmp_path / "protocol.json"
    request.write_text(
        json.dumps(
            {
                "session_id": "ses_example",
                "harness": "codex",
                "model_route": {
                    "coordinator": "economy",
                    "exploration": "balanced",
                    "execution": "none",
                    "verification": "frontier",
                },
                "evidence_required": ["regression-test"],
                "budget_limit_usd": "0.25",
            }
        )
    )

    assert main(["delegation", "compile", str(tmp_path), str(request)]) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["schema"] == "trufagent.delegation.v1"
    assert result["max_parallel"] == 1
    assert result["steps"][2]["model"] is None
    assert result["steps"][3]["required_evidence"] == ["regression-test"]


def test_cli_appends_and_summarizes_usage(tmp_path: Path, capsys) -> None:
    from datetime import UTC, datetime

    record_path = tmp_path / "usage.json"
    record_path.write_text(
        UsageRecord(
            schema="trufagent.usage.v1",
            invocation_id="inv_001",
            session_id="ses_example",
            recorded_at=datetime(2026, 7, 31, tzinfo=UTC),
            phase=DelegationPhase.EXPLORATION,
            harness=Harness.CODEX,
            model="gpt-5.6-terra",
            input_tokens=100,
        ).model_dump_json(by_alias=True)
    )

    assert main(["delegation", "usage", "append", str(tmp_path), str(record_path)]) == 0
    capsys.readouterr()
    assert (
        main(
            [
                "delegation",
                "usage",
                "status",
                str(tmp_path),
                "ses_example",
                "--budget-limit-usd",
                "0.50",
            ]
        )
        == 0
    )
    status = json.loads(capsys.readouterr().out)
    assert status == {
        "session_id": "ses_example",
        "records": 1,
        "known_cost_usd": "0",
        "reserved_cost_usd": "0",
        "has_unknown_cost": True,
        "has_unbounded_unknown_cost": True,
        "cost_status": "unknown",
        "remaining_budget_usd": "0.50",
        "budget_limit_usd": "0.50",
    }


def test_cli_dry_run_returns_stable_harness_observation(tmp_path: Path, capsys) -> None:
    protocol = tmp_path / "protocol.json"
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "session_id": "ses_example",
                "harness": "codex",
                "model_route": {
                    "coordinator": "economy",
                    "exploration": "none",
                    "execution": "economy",
                    "verification": "frontier",
                },
                "evidence_required": ["tests"],
            }
        )
    )
    assert main(["delegation", "compile", str(tmp_path), str(request)]) == 0
    protocol.write_text(capsys.readouterr().out)
    script = tmp_path / "script.json"
    script.write_text(
        json.dumps(
            {
                "coordinator": {
                    "phase": "coordinator",
                    "status": "success",
                    "summary": "Ready.",
                },
                "execution": {
                    "phase": "execution",
                    "status": "success",
                    "summary": "Applied.",
                    "worktree_changed": True,
                },
                "verification": {
                    "phase": "verification",
                    "status": "success",
                    "summary": "Passed.",
                    "evidence": ["tests"],
                    "artifacts": ["report.json"],
                },
            }
        )
    )

    assert main(["delegation", "dry-run", str(protocol), str(script)]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["status"] == "success"
    assert report["summary"]
    assert report["next_actions"]
    assert report["artifacts"] == ["report.json"]
    assert [item["status"] for item in report["handoffs"]] == [
        "success",
        "skipped",
        "success",
        "success",
    ]
