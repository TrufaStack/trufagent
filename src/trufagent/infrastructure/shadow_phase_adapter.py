from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from trufagent.domain.attempt import (
    AttemptEvent,
    AttemptStatus,
    FailureKind,
    ProviderEventType,
)
from trufagent.domain.delegation import (
    ActionScope,
    DelegationPhase,
    DelegationStep,
    HandoffStatus,
    PhaseHandoff,
    UsageRecord,
)
from trufagent.domain.task import Harness
from trufagent.infrastructure.attempt_fs import JsonlAttemptRepository
from trufagent.infrastructure.usage_fs import JsonlUsageRepository
from trufagent.infrastructure.worktree_fingerprint import fingerprint_worktree


@dataclass(frozen=True, slots=True)
class ShadowProgress:
    elapsed_ms: int = 0
    event_count: int = 0
    first_event_type: ProviderEventType | str | None = None


@dataclass(frozen=True, slots=True)
class ShadowResult:
    handoff: PhaseHandoff
    usage: UsageRecord
    progress: ShadowProgress = ShadowProgress()


class ShadowRunner(Protocol):
    def run(
        self,
        step: DelegationStep,
        previous: tuple[PhaseHandoff, ...],
    ) -> ShadowResult: ...


class ShadowPhaseAdapter:
    """Read-only provider boundary with content fingerprint and usage accounting."""

    _ALLOWED_PHASES = {
        DelegationPhase.COORDINATOR,
        DelegationPhase.EXPLORATION,
    }

    def __init__(
        self,
        *,
        project_root: Path,
        session_id: str,
        harness: Harness,
        runner: ShadowRunner,
        usage: JsonlUsageRepository,
        attempts: JsonlAttemptRepository | None = None,
        task_digest: str | None = None,
        attempt: int = 1,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.session_id = session_id
        self.harness = harness
        self.runner = runner
        self.usage = usage
        self.attempts = attempts
        self.task_digest = task_digest
        self.attempt = attempt

    def invoke(
        self,
        step: DelegationStep,
        previous: tuple[PhaseHandoff, ...],
    ) -> PhaseHandoff:
        if step.phase not in self._ALLOWED_PHASES:
            raise ValueError(f"shadow phase is not allowed: {step.phase.value}")
        if step.action_scope != ActionScope.READ_ONLY:
            raise ValueError("shadow adapter requires read-only action scope")
        before = fingerprint_worktree(self.project_root)
        attempt_id = f"att_{secrets.token_hex(8)}"
        self._record(
            step,
            attempt_id,
            status=AttemptStatus.STARTED,
        )
        try:
            result = self.runner.run(step, previous)
        except Exception as exc:
            failed_usage = getattr(exc, "usage", None)
            if isinstance(failed_usage, UsageRecord):
                self._validate_usage(step, failed_usage)
                self.usage.append(failed_usage)
            after = fingerprint_worktree(self.project_root)
            progress = getattr(exc, "progress", None)
            self._record(
                step,
                attempt_id,
                status=AttemptStatus.FAILED,
                failure_kind=self._failure_kind(exc),
                worktree_unchanged=before == after,
                progress=progress if isinstance(progress, ShadowProgress) else None,
            )
            raise
        after = fingerprint_worktree(self.project_root)
        self._validate_usage(step, result.usage)
        self.usage.append(result.usage)
        if before != after:
            self._record(
                step,
                attempt_id,
                status=AttemptStatus.FAILED,
                failure_kind=FailureKind.WORKTREE_CHANGE,
                worktree_unchanged=False,
                progress=result.progress,
            )
            return PhaseHandoff(
                phase=step.phase,
                status=HandoffStatus.ERROR,
                summary="Shadow invocation changed protected worktree content.",
                root_cause_hint="The provider crossed the read-only boundary.",
                safe_retry="Restore the changed content, then use the scripted dry-run.",
                stop_condition="Do not invoke another provider in this session.",
                worktree_changed=True,
            )
        self._record(
            step,
            attempt_id,
            status=AttemptStatus.SUCCEEDED,
            worktree_unchanged=True,
            progress=result.progress,
        )
        return result.handoff.model_copy(update={"worktree_changed": False})

    def _record(
        self,
        step: DelegationStep,
        attempt_id: str,
        *,
        status: AttemptStatus,
        failure_kind: FailureKind | None = None,
        worktree_unchanged: bool | None = None,
        progress: ShadowProgress | None = None,
    ) -> None:
        if self.attempts is None:
            return
        if self.task_digest is None:
            raise ValueError("attempt repository requires a task digest")
        event = AttemptEvent(
            schema="trufagent.attempt.v1",
            event_id=f"evt_{secrets.token_hex(12)}",
            attempt_id=attempt_id,
            session_id=self.session_id,
            task_digest=self.task_digest,
            phase=step.phase,
            attempt=self.attempt,
            status=status,
            created_at=datetime.now(UTC),
            failure_kind=failure_kind,
            worktree_unchanged=worktree_unchanged,
            elapsed_ms=progress.elapsed_ms if progress is not None else None,
            observed_events=progress.event_count if progress is not None else None,
            first_event_type=progress.first_event_type if progress is not None else None,
        )
        self.attempts.append(event)

    @staticmethod
    def _failure_kind(exc: Exception) -> FailureKind:
        name = type(exc).__name__
        if name == "ShadowTimeoutError":
            return FailureKind.PROVIDER_TIMEOUT
        if name == "ShadowProcessError":
            return FailureKind.TRANSIENT_PROCESS
        if name == "ShadowResponseError":
            return FailureKind.INVALID_RESPONSE
        return FailureKind.ACCEPTANCE_GATE

    def _validate_usage(self, step: DelegationStep, record: UsageRecord) -> None:
        expected = (self.session_id, step.phase, self.harness, step.model)
        observed = (
            record.session_id,
            record.phase,
            record.harness,
            record.model,
        )
        if observed != expected:
            raise ValueError("shadow usage metadata does not match the invocation")
