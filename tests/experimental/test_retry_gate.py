import pytest

from trufagent.experimental.retry_gate import (
    FailureKind,
    evaluate_supervised_retry,
)


def test_transient_process_failure_can_receive_one_supervised_retry() -> None:
    gate = evaluate_supervised_retry(
        failure_kind=FailureKind.TRANSIENT_PROCESS,
        prior_attempts=1,
        worktree_unchanged=True,
        budget_authorized=True,
        human_confirmed=True,
    )

    assert gate.allowed is True
    assert gate.authorized_attempt == 2


@pytest.mark.parametrize(
    "override",
    [
        {"failure_kind": FailureKind.INVALID_RESPONSE},
        {"failure_kind": FailureKind.ACCEPTANCE_GATE},
        {"failure_kind": FailureKind.WORKTREE_CHANGE},
        {"prior_attempts": 2},
        {"worktree_unchanged": False},
        {"budget_authorized": False},
        {"human_confirmed": False},
    ],
)
def test_retry_fails_closed_when_any_guard_is_missing(override) -> None:
    request = {
        "failure_kind": FailureKind.TRANSIENT_PROCESS,
        "prior_attempts": 1,
        "worktree_unchanged": True,
        "budget_authorized": True,
        "human_confirmed": True,
    }
    request.update(override)

    gate = evaluate_supervised_retry(**request)

    assert gate.allowed is False
    assert gate.authorized_attempt is None
    assert gate.reasons
