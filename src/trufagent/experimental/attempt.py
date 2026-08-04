from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trufagent.experimental.delegation_domain import DelegationPhase


class FailureKind(StrEnum):
    TRANSIENT_PROCESS = "transient-process"
    PROVIDER_TIMEOUT = "provider-timeout"
    INVALID_RESPONSE = "invalid-response"
    ACCEPTANCE_GATE = "acceptance-gate"
    WORKTREE_CHANGE = "worktree-change"
    BUDGET = "budget"


class ProviderEventType(StrEnum):
    THREAD_STARTED = "thread-started"
    TURN_STARTED = "turn-started"
    ITEM_COMPLETED = "item-completed"
    TURN_COMPLETED = "turn-completed"
    OTHER = "other"


class AttemptStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AttemptEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.attempt\.v1$")
    event_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    task_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    phase: DelegationPhase
    attempt: int = Field(ge=1, le=2)
    status: AttemptStatus
    created_at: datetime
    failure_kind: FailureKind | None = None
    worktree_unchanged: bool | None = None
    elapsed_ms: int | None = Field(default=None, ge=0)
    observed_events: int | None = Field(default=None, ge=0)
    first_event_type: ProviderEventType | None = None

    @model_validator(mode="after")
    def terminal_fields_match_status(self) -> AttemptEvent:
        if self.status == AttemptStatus.STARTED and (
            self.failure_kind is not None
            or self.worktree_unchanged is not None
            or self.elapsed_ms is not None
            or self.observed_events is not None
            or self.first_event_type is not None
        ):
            raise ValueError("started attempts cannot contain terminal facts")
        if self.status == AttemptStatus.SUCCEEDED and self.failure_kind is not None:
            raise ValueError("successful attempts cannot contain a failure kind")
        if self.status != AttemptStatus.STARTED and self.worktree_unchanged is None:
            raise ValueError("terminal attempts require a worktree fact")
        if self.status == AttemptStatus.FAILED and self.failure_kind is None:
            raise ValueError("failed attempts require a failure kind")
        return self
