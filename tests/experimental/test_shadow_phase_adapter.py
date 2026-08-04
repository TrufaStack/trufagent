from datetime import UTC, datetime
from pathlib import Path

from trufagent.domain.task import Harness, ModelTier
from trufagent.experimental.attempt import FailureKind
from trufagent.experimental.attempt_fs import JsonlAttemptRepository
from trufagent.experimental.codex_shadow_runner import (
    ShadowResponseCode,
    ShadowResponseError,
    ShadowTimeoutError,
)
from trufagent.experimental.delegation_domain import (
    ActionScope,
    DelegationPhase,
    DelegationStep,
    HandoffStatus,
    PhaseHandoff,
    UsageRecord,
)
from trufagent.experimental.shadow_phase_adapter import (
    ShadowPhaseAdapter,
    ShadowProgress,
    ShadowResult,
)
from trufagent.experimental.usage_fs import JsonlUsageRepository


class FakeShadowRunner:
    def __init__(self, root: Path, *, mutate: bool = False) -> None:
        self.root = root
        self.mutate = mutate
        self.calls = 0

    def run(self, step, previous) -> ShadowResult:
        del previous
        self.calls += 1
        if self.mutate:
            (self.root / "untracked.py").write_text("changed")
        return ShadowResult(
            handoff=PhaseHandoff(
                phase=step.phase,
                status=HandoffStatus.SUCCESS,
                summary="Read-only exploration completed.",
            ),
            usage=UsageRecord(
                schema="trufagent.usage.v1",
                invocation_id=f"inv_{self.calls}",
                session_id="ses_example",
                recorded_at=datetime(2026, 7, 31, tzinfo=UTC),
                phase=step.phase,
                harness=Harness.CODEX,
                model=step.model,
                input_tokens=100,
                output_tokens=10,
            ),
        )


def _step(phase: DelegationPhase = DelegationPhase.EXPLORATION) -> DelegationStep:
    return DelegationStep(
        phase=phase,
        tier=ModelTier.BALANCED,
        model="gpt-5.6-terra",
        action_scope=(
            ActionScope.WORKTREE_WRITE
            if phase == DelegationPhase.EXECUTION
            else ActionScope.READ_ONLY
        ),
        max_attempts=1,
    )


def _adapter(tmp_path: Path, runner: FakeShadowRunner) -> ShadowPhaseAdapter:
    return ShadowPhaseAdapter(
        project_root=tmp_path,
        session_id="ses_example",
        harness=Harness.CODEX,
        runner=runner,
        usage=JsonlUsageRepository(tmp_path),
    )


def test_shadow_accepts_read_only_handoff_and_records_usage(tmp_path: Path) -> None:
    (tmp_path / "untracked.py").write_text("stable")
    runner = FakeShadowRunner(tmp_path)

    handoff = _adapter(tmp_path, runner).invoke(_step(), ())

    assert handoff.status == HandoffStatus.SUCCESS
    ledger = JsonlUsageRepository(tmp_path).load("ses_example")
    assert len(ledger.records) == 1
    assert ledger.has_unknown_cost is True


def test_shadow_detects_content_change_even_when_file_was_already_untracked(
    tmp_path: Path,
) -> None:
    (tmp_path / "untracked.py").write_text("stable")
    runner = FakeShadowRunner(tmp_path, mutate=True)

    handoff = _adapter(tmp_path, runner).invoke(_step(), ())

    assert handoff.status == HandoffStatus.ERROR
    assert handoff.worktree_changed is True
    assert runner.calls == 1
    assert len(JsonlUsageRepository(tmp_path).load("ses_example").records) == 1


def test_shadow_refuses_execution_phase_before_calling_runner(tmp_path: Path) -> None:
    runner = FakeShadowRunner(tmp_path)

    try:
        _adapter(tmp_path, runner).invoke(_step(DelegationPhase.EXECUTION), ())
    except ValueError as exc:
        assert "not allowed" in str(exc)
    else:
        raise AssertionError("execution phase should be rejected")

    assert runner.calls == 0


def test_invalid_response_records_unknown_cost_before_failing(tmp_path: Path) -> None:
    class InvalidResponseRunner:
        def run(self, step, previous):
            del previous
            raise ShadowResponseError(
                ShadowResponseCode.HANDOFF_SCHEMA_INVALID,
                usage=UsageRecord(
                    schema="trufagent.usage.v1",
                    invocation_id="inv_invalid",
                    session_id="ses_example",
                    recorded_at=datetime(2026, 7, 31, tzinfo=UTC),
                    phase=step.phase,
                    harness=Harness.CODEX,
                    model=step.model,
                    input_tokens=100,
                    output_tokens=10,
                ),
            )

    adapter = _adapter(tmp_path, InvalidResponseRunner())

    try:
        adapter.invoke(_step(), ())
    except ShadowResponseError:
        pass
    else:
        raise AssertionError("invalid response should fail the shadow invocation")

    ledger = JsonlUsageRepository(tmp_path).load("ses_example")
    assert len(ledger.records) == 1
    assert ledger.has_unknown_cost is True


def test_timeout_records_unknown_cost_and_has_terminal_failure_kind(tmp_path: Path) -> None:
    class TimeoutRunner:
        def run(self, step, previous):
            del previous
            raise ShadowTimeoutError(
                usage=UsageRecord(
                    schema="trufagent.usage.v1",
                    invocation_id="inv_timeout",
                    session_id="ses_example",
                    recorded_at=datetime(2026, 8, 3, tzinfo=UTC),
                    phase=step.phase,
                    harness=Harness.CODEX,
                    model=step.model,
                ),
                progress=ShadowProgress(
                    elapsed_ms=180_000,
                    event_count=3,
                    first_event_type="thread-started",
                ),
            )

    attempts = JsonlAttemptRepository(tmp_path)
    adapter = ShadowPhaseAdapter(
        project_root=tmp_path,
        session_id="ses_example",
        harness=Harness.CODEX,
        runner=TimeoutRunner(),
        usage=JsonlUsageRepository(tmp_path),
        attempts=attempts,
        task_digest="a" * 64,
    )

    try:
        adapter.invoke(_step(), ())
    except ShadowTimeoutError:
        pass
    else:
        raise AssertionError("timeout should fail the shadow invocation")

    ledger = JsonlUsageRepository(tmp_path).load("ses_example")
    assert len(ledger.records) == 1
    assert ledger.has_unknown_cost is True
    terminal = attempts.load("ses_example")[-1]
    assert terminal.elapsed_ms == 180_000
    assert terminal.observed_events == 3
    assert terminal.first_event_type == "thread-started"
    assert adapter._failure_kind(
        ShadowTimeoutError(usage=ledger.records[0], progress=ShadowProgress())
    ) == (
        FailureKind.PROVIDER_TIMEOUT
    )
