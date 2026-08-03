from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from trufagent.domain.attempt import FailureKind
from trufagent.domain.delegation import HandoffStatus


class RetryGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: HandoffStatus
    summary: str
    next_actions: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    allowed: bool
    reasons: tuple[str, ...] = ()
    authorized_attempt: int | None = Field(default=None, ge=2, le=2)


def evaluate_supervised_retry(
    *,
    failure_kind: FailureKind,
    prior_attempts: int,
    worktree_unchanged: bool,
    budget_authorized: bool,
    human_confirmed: bool,
) -> RetryGateResult:
    reasons: list[str] = []
    if failure_kind != FailureKind.TRANSIENT_PROCESS:
        reasons.append(f"{failure_kind.value} is not retryable")
    if prior_attempts != 1:
        reasons.append("exactly one prior attempt is required")
    if not worktree_unchanged:
        reasons.append("protected worktree content changed")
    if not budget_authorized:
        reasons.append("retry budget is not authorized")
    if not human_confirmed:
        reasons.append("human confirmation is required")
    if reasons:
        return RetryGateResult(
            status=HandoffStatus.WARNING,
            summary="Supervised retry is not authorized.",
            next_actions=("Return control to the host coordinator.",),
            allowed=False,
            reasons=tuple(reasons),
        )
    return RetryGateResult(
        status=HandoffStatus.SUCCESS,
        summary="One supervised transient-process retry is authorized.",
        next_actions=("Create a new invocation id and run exactly one attempt.",),
        allowed=True,
        authorized_attempt=2,
    )
