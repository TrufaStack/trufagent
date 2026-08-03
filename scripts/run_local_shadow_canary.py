#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from trufagent.cli import main as cli_main
from trufagent.domain.attempt import AttemptStatus
from trufagent.domain.delegation import (
    HandoffStatus,
    PhaseHandoff,
    UsageRecord,
)
from trufagent.domain.task import Harness, ModelTier
from trufagent.infrastructure.attempt_fs import JsonlAttemptRepository
from trufagent.infrastructure.shadow_phase_adapter import ShadowResult
from trufagent.infrastructure.usage_fs import JsonlUsageRepository

TASK = "Diagnose why saved answers disappear and no error is shown."
SYMBOL = "resolveChecklistJobType"


def _call(arguments: list[str]) -> tuple[int, dict]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = cli_main(arguments)
    output = stdout.getvalue().strip() or stderr.getvalue().strip()
    return exit_code, json.loads(output)


def run_canary(project_root: Path) -> dict:
    root = Path(project_root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    task_exit, preview = _call(
        [
            "task",
            TASK,
            "--root",
            str(root),
            "--project",
            "local-shadow-canary",
            "--kind",
            "bug",
            "--no-cause-known",
            "--required-symbol",
            SYMBOL,
        ]
    )
    if task_exit != 0:
        raise RuntimeError("canary preview was not ready")

    continuation_exit, authorization = _call(
        [
            "task-continue",
            preview["preview_id"],
            "--root",
            str(root),
            "--mode",
            "shadow",
            "--task-text",
            TASK,
            "--confirm",
        ]
    )
    if continuation_exit != 0:
        raise RuntimeError("canary continuation was not authorized")

    observed: dict[str, object] = {"calls": 0}

    class LocalRunner:
        def __init__(self, **kwargs):
            observed["task"] = kwargs["task"]

        def run(self, step, previous):
            observed["calls"] = int(observed["calls"]) + 1
            observed["tier"] = step.tier.value
            observed["model"] = step.model
            observed["previous_phases"] = [handoff.phase.value for handoff in previous]
            return ShadowResult(
                handoff=PhaseHandoff(
                    phase=step.phase,
                    status=HandoffStatus.SUCCESS,
                    summary="Simulated read-only exploration completed.",
                    evidence=("simulated-source-inspection",),
                ),
                usage=UsageRecord(
                    schema="trufagent.usage.v1",
                    invocation_id="inv_local_shadow_canary",
                    session_id=preview["session_id"],
                    recorded_at=datetime.now(UTC),
                    phase=step.phase,
                    harness=Harness.CODEX,
                    model=step.model,
                    input_tokens=200,
                    cached_input_tokens=100,
                    output_tokens=40,
                    cost_usd=Decimal("0.02"),
                ),
            )

    invocation = [
        "delegation",
        "shadow",
        str(root),
        "--session",
        preview["session_id"],
        "--task",
        TASK,
        "--preview",
        preview["preview_id"],
        "--budget-limit-usd",
        "0.10",
        "--estimated-cost-usd",
        "0.05",
        "--confirm-provider",
    ]
    with patch("trufagent.cli.CodexShadowRunner", LocalRunner):
        run_exit, run_report = _call(invocation)
        budget_exit, budget_report = _call(
            [
                *invocation[:-2],
                "0.09",
                "--confirm-provider",
            ]
        )

    attempts = JsonlAttemptRepository(root).load(preview["session_id"])
    ledger = JsonlUsageRepository(root).load(
        preview["session_id"],
        budget_limit_usd=Decimal("0.10"),
    )
    judges = {
        "preview_integrity": (
            preview["required_symbols"] == [SYMBOL]
            and authorization["required_symbols"] == [SYMBOL]
            and authorization["model_tier"] == "frontier"
        ),
        "route_integrity": (
            observed.get("tier") == ModelTier.FRONTIER.value
            and observed.get("model") == "gpt-5.6-sol"
        ),
        "handoff_integrity": (
            run_exit == 0
            and run_report["status"] == "success"
            and [item["status"] for item in run_report["handoffs"]]
            == ["skipped", "success", "skipped", "skipped"]
        ),
        "accounting_integrity": (
            [(event.attempt, event.status) for event in attempts]
            == [(1, AttemptStatus.STARTED), (1, AttemptStatus.SUCCEEDED)]
            and ledger.known_cost_usd == Decimal("0.02")
            and ledger.has_unknown_cost is False
        ),
        "budget_fail_closed": (
            budget_exit == 1
            and "exceed session budget" in budget_report["summary"]
            and observed["calls"] == 1
        ),
    }
    return {
        "schema": "trufagent.local-shadow-canary.v1",
        "status": "passed" if all(judges.values()) else "failed",
        "provider_invocations": 0,
        "simulated_runner_calls": observed["calls"],
        "known_cost_usd": str(ledger.known_cost_usd),
        "judges": judges,
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="trufagent-shadow-canary-") as directory:
        print(json.dumps(run_canary(Path(directory)), sort_keys=True))


if __name__ == "__main__":
    main()
