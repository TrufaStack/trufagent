import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trufagent.cli import _shadow_schema_path, main
from trufagent.domain.task import Harness, ModelTier, TaskSignals
from trufagent.experimental.attempt import AttemptEvent, AttemptStatus, FailureKind
from trufagent.experimental.attempt_fs import JsonlAttemptRepository
from trufagent.experimental.codex_shadow_runner import (
    ShadowProcessError,
    ShadowTimeoutError,
)
from trufagent.experimental.delegation_domain import (
    DelegationPhase,
    HandoffStatus,
    PhaseHandoff,
    UsageRecord,
)
from trufagent.experimental.shadow_phase_adapter import ShadowResult
from trufagent.experimental.usage_fs import JsonlUsageRepository


def _signals(tmp_path: Path) -> Path:
    path = tmp_path / "signals.json"
    path.write_text(
        json.dumps({"kind": "architecture", "open_decisions": True}),
        encoding="utf-8",
    )
    return path


def test_shadow_schema_is_packaged_with_trufagent_not_required_from_project(
    tmp_path: Path,
) -> None:
    schema = _shadow_schema_path()

    assert schema.is_file()
    assert tmp_path not in schema.parents
    assert schema.name == "handoff-schema.json"
    status = json.loads(schema.read_text())["properties"]["status"]
    assert status["enum"] == ["success", "warning"]
    inspected = json.loads(schema.read_text())["properties"]["inspected_files"]
    assert inspected["maxItems"] == 12


def _seed_failed_attempt(tmp_path: Path, signals_path: Path, kind: FailureKind) -> None:
    signals = TaskSignals.model_validate_json(signals_path.read_text())
    payload = json.dumps(
        {
            "task": "Choose an architecture",
            "signals": signals.model_dump(mode="json"),
            "required_symbols": ["SomeSymbol"],
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    repository = JsonlAttemptRepository(tmp_path)
    common = {
        "schema": "trufagent.attempt.v1",
        "attempt_id": "att_prior",
        "session_id": "ses_test",
        "task_digest": digest,
        "phase": DelegationPhase.EXPLORATION,
        "attempt": 1,
        "created_at": datetime(2026, 7, 31, tzinfo=UTC),
    }
    repository.append(
        AttemptEvent(
            **common,
            event_id="evt_started",
            status=AttemptStatus.STARTED,
        )
    )
    repository.append(
        AttemptEvent(
            **common,
            event_id="evt_failed",
            status=AttemptStatus.FAILED,
            failure_kind=kind,
            worktree_unchanged=True,
        )
    )


def test_shadow_prepares_without_query_or_provider_by_default(
    tmp_path: Path,
    capsys,
) -> None:
    signals_path = _signals(tmp_path)
    _seed_failed_attempt(tmp_path, signals_path, FailureKind.TRANSIENT_PROCESS)
    result = main(
        [
            "delegation",
            "shadow",
            str(tmp_path),
            "--session",
            "ses_test",
            "--task",
            "Choose an architecture",
            "--signals",
            str(signals_path),
            "--required-symbol",
            "SomeSymbol",
            "--budget-limit-usd",
            "0.50",
            "--estimated-cost-usd",
            "0.10",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert result == 1
    assert output["disposition"] == "shadow-required"
    assert output["graph_queries"] == 0
    assert output["model_invocations"] == 0
    preflight = output["preflight"]
    assert preflight["schema"] == "trufagent.shadow-preflight.v1"
    assert preflight["status"] == "ready"
    assert preflight["model"] == "gpt-5.6-sol"
    assert preflight["tier"] == "balanced"
    assert preflight["budget_limit_usd"] == "0.50"
    assert preflight["authorized_estimate_usd"] == "0.10"
    assert preflight["target_count"] == 0
    assert preflight["target_limit"] == 24
    assert preflight["file_limit"] == 12
    assert preflight["timeout_seconds"] == 180
    assert preflight["prompt_chars"] > 0
    assert preflight["read_only"] is True
    assert "task" not in preflight


def test_second_attempt_fails_closed_without_retry_confirmation(
    tmp_path: Path,
    capsys,
) -> None:
    signals_path = _signals(tmp_path)
    _seed_failed_attempt(tmp_path, signals_path, FailureKind.TRANSIENT_PROCESS)
    result = main(
        [
            "delegation",
            "shadow",
            str(tmp_path),
            "--session",
            "ses_test",
            "--task",
            "Choose an architecture",
            "--signals",
            str(signals_path),
            "--required-symbol",
            "SomeSymbol",
            "--budget-limit-usd",
            "0.50",
            "--estimated-cost-usd",
            "0.10",
            "--confirm-provider",
            "--attempt",
            "2",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert result == 1
    assert output["allowed"] is False
    assert "human confirmation is required" in output["reasons"]


def test_second_attempt_rejects_non_transient_failure(
    tmp_path: Path,
    capsys,
) -> None:
    signals_path = _signals(tmp_path)
    _seed_failed_attempt(tmp_path, signals_path, FailureKind.INVALID_RESPONSE)
    result = main(
        [
            "delegation",
            "shadow",
            str(tmp_path),
            "--session",
            "ses_test",
            "--task",
            "Choose an architecture",
            "--signals",
            str(signals_path),
            "--required-symbol",
            "SomeSymbol",
            "--budget-limit-usd",
            "0.50",
            "--estimated-cost-usd",
            "0.10",
            "--confirm-provider",
            "--attempt",
            "2",
            "--confirm-retry",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert result == 1
    assert output["allowed"] is False
    assert "invalid-response is not retryable" in output["reasons"]


def test_transient_first_attempt_can_be_retried_once_from_durable_history(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    signals_path = _signals(tmp_path)

    class FakeRunner:
        calls = 0
        tiers = []

        def __init__(self, **kwargs):
            del kwargs

        def run(self, step, previous):
            del previous
            type(self).calls += 1
            type(self).tiers.append(step.tier)
            if self.calls == 1:
                raise ShadowProcessError("Codex shadow process-exit-1")
            return ShadowResult(
                handoff=PhaseHandoff(
                    phase=step.phase,
                    status=HandoffStatus.SUCCESS,
                    summary="Recovered read-only exploration.",
                ),
                usage=UsageRecord(
                    schema="trufagent.usage.v1",
                    invocation_id="inv_retry",
                    session_id="ses_test",
                    recorded_at=datetime(2026, 7, 31, tzinfo=UTC),
                    phase=step.phase,
                    harness=Harness.CODEX,
                    model=step.model,
                    input_tokens=10,
                    output_tokens=2,
                ),
            )

    monkeypatch.setattr("trufagent.cli.CodexShadowRunner", FakeRunner)
    base = [
        "delegation",
        "shadow",
        str(tmp_path),
        "--session",
        "ses_test",
        "--task",
        "Choose an architecture",
        "--signals",
        str(signals_path),
        "--required-symbol",
        "SomeSymbol",
        "--budget-limit-usd",
        "0.50",
        "--estimated-cost-usd",
        "0.10",
        "--confirm-provider",
        "--tier",
        "frontier",
    ]

    assert main(base) == 1
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "error"

    assert main([*base, "--attempt", "2", "--confirm-retry"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["status"] == "success"

    events = JsonlAttemptRepository(tmp_path).load("ses_test")
    assert [(event.attempt, event.status) for event in events] == [
        (1, AttemptStatus.STARTED),
        (1, AttemptStatus.FAILED),
        (2, AttemptStatus.STARTED),
        (2, AttemptStatus.SUCCEEDED),
    ]
    assert FakeRunner.tiers == [ModelTier.FRONTIER, ModelTier.FRONTIER]


def test_timeout_records_unknown_cost_and_blocks_later_provider_authorization(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    signals_path = _signals(tmp_path)

    class TimeoutRunner:
        def __init__(self, **kwargs):
            self.session_id = kwargs["session_id"]

        def run(self, step, previous):
            del previous
            raise ShadowTimeoutError(
                usage=UsageRecord(
                    schema="trufagent.usage.v1",
                    invocation_id="inv_timeout",
                    session_id=self.session_id,
                    recorded_at=datetime(2026, 8, 3, tzinfo=UTC),
                    phase=step.phase,
                    harness=Harness.CODEX,
                    model=step.model,
                )
            )

    monkeypatch.setattr("trufagent.cli.CodexShadowRunner", TimeoutRunner)
    command = [
        "delegation",
        "shadow",
        str(tmp_path),
        "--session",
        "ses_test",
        "--task",
        "Choose an architecture",
        "--signals",
        str(signals_path),
        "--required-symbol",
        "SomeSymbol",
        "--budget-limit-usd",
        "0.50",
        "--estimated-cost-usd",
        "0.10",
        "--confirm-provider",
    ]

    assert main(command) == 1
    capsys.readouterr()
    ledger = JsonlUsageRepository(tmp_path).load("ses_test")
    assert ledger.has_unknown_cost is True
    digest = hashlib.sha256(
            json.dumps(
                {
                    "task": "Choose an architecture",
                    "signals": TaskSignals.model_validate_json(
                        signals_path.read_text()
                    ).model_dump(mode="json"),
                    "required_symbols": ["SomeSymbol"],
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
    events = JsonlAttemptRepository(tmp_path).for_task("ses_test", digest)
    failed = [event for event in events if event.status == AttemptStatus.FAILED]
    assert len(failed) == 1
    assert failed[0].failure_kind == FailureKind.PROVIDER_TIMEOUT

    assert main(command) == 1
    error = json.loads(capsys.readouterr().err)
    assert "prior session cost is unknown" in error["summary"]


def test_shadow_preview_binds_symbols_signals_and_frontier_tier(
    tmp_path: Path,
    capsys,
    monkeypatch,
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
    assert (
        main(
            [
                "delegation",
                "shadow",
                str(tmp_path),
                "--session",
                preview["session_id"],
                "--task",
                task,
                "--preview",
                preview["preview_id"],
                "--budget-limit-usd",
                "0.10",
                "--estimated-cost-usd",
                "0.05",
            ]
        )
        == 1
    )
    prepared = json.loads(capsys.readouterr().out)
    assert prepared["preflight"]["session_active"] is True
    assert prepared["preflight"]["preview_fresh"] is True
    observed = {}

    class FakeRunner:
        def __init__(self, **kwargs):
            observed["model"] = kwargs.get("task")
            observed["required_symbols"] = kwargs.get("required_symbols")
            observed["structural_targets"] = kwargs.get("structural_targets")
            observed["authorized_estimate_usd"] = kwargs.get(
                "authorized_estimate_usd"
            )

        def run(self, step, previous):
            del previous
            observed["tier"] = step.tier
            observed["step_model"] = step.model
            return ShadowResult(
                handoff=PhaseHandoff(
                    phase=step.phase,
                    status=HandoffStatus.SUCCESS,
                    summary="Read-only cause confirmed.",
                ),
                usage=UsageRecord(
                    schema="trufagent.usage.v1",
                    invocation_id="inv_preview",
                    session_id=preview["session_id"],
                    recorded_at=datetime(2026, 8, 3, tzinfo=UTC),
                    phase=step.phase,
                    harness=Harness.CODEX,
                    model=step.model,
                    input_tokens=20,
                    output_tokens=5,
                ),
            )

    monkeypatch.setattr("trufagent.cli.CodexShadowRunner", FakeRunner)
    assert (
        main(
            [
                "delegation",
                "shadow",
                str(tmp_path),
                "--session",
                preview["session_id"],
                "--task",
                task,
                "--preview",
                preview["preview_id"],
                "--budget-limit-usd",
                "0.10",
                "--estimated-cost-usd",
                "0.05",
                "--confirm-provider",
            ]
        )
        == 0
    )

    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "success"
    assert observed["tier"] == ModelTier.FRONTIER
    assert observed["step_model"] == "gpt-5.6-sol"
    assert observed["required_symbols"] == ["resolveChecklistJobType"]
    assert observed["structural_targets"] == []
    assert observed["authorized_estimate_usd"] == Decimal("0.05")
    events = JsonlAttemptRepository(tmp_path).load(preview["session_id"])
    assert len(events) == 2


def test_shadow_preview_fails_before_provider_when_worktree_changed(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    task = "Diagnose why saved answers disappear."
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
    (tmp_path / "changed-after-preview.ts").write_text("export const changed = true;\n")

    class ProviderMustNotStart:
        def __init__(self, **kwargs):
            raise AssertionError("stale preview must fail before provider setup")

    monkeypatch.setattr("trufagent.cli.CodexShadowRunner", ProviderMustNotStart)
    result = main(
        [
            "delegation",
            "shadow",
            str(tmp_path),
            "--session",
            preview["session_id"],
            "--task",
            task,
            "--preview",
            preview["preview_id"],
            "--budget-limit-usd",
            "0.10",
            "--estimated-cost-usd",
            "0.05",
        ]
    )

    error = json.loads(capsys.readouterr().err)
    assert result == 1
    assert "worktree changed since preview" in error["summary"]


def test_shadow_preview_requires_its_active_session(
    tmp_path: Path,
    capsys,
) -> None:
    task = "Diagnose why saved answers disappear."
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
    current = tmp_path / ".trufagent" / "state" / "current-session.yaml"
    current.unlink()

    result = main(
        [
            "delegation",
            "shadow",
            str(tmp_path),
            "--session",
            preview["session_id"],
            "--task",
            task,
            "--preview",
            preview["preview_id"],
            "--budget-limit-usd",
            "0.10",
            "--estimated-cost-usd",
            "0.05",
        ]
    )

    error = json.loads(capsys.readouterr().err)
    assert result == 1
    assert "active session" in error["summary"]
