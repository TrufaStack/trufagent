import pytest
from pydantic import ValidationError

from trufagent.domain.observation import Observation, OperationError, OperationStatus


def test_success_observation_has_deterministic_shape() -> None:
    result = Observation[dict](
        status=OperationStatus.SUCCESS,
        summary="Memory validated",
        next_actions=[],
        artifacts=["mem_C05_SAFE_DIAGNOSTICS"],
        data={"valid": True},
    )

    assert result.error is None
    assert result.model_dump(mode="json")["status"] == "success"


def test_operation_error_requires_stop_condition() -> None:
    with pytest.raises(ValidationError):
        OperationError(code="graph_stale", root_cause_hint="HEAD changed")
