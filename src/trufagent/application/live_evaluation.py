from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from trufagent.domain.task import AutonomyBoundary, EffortLevel


class LiveExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ready_to_plan: bool
    autonomy: AutonomyBoundary
    exploration: EffortLevel
    execution: EffortLevel
    verification: EffortLevel
    user_action: str


class LiveResponse(LiveExpectation):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    skill_invoked: bool
    runtime_called: bool
    implementation_started: bool
    diagnostic_command_ran: bool
    summary: str


class LiveJudgeResult(BaseModel):
    passed: bool
    dimensions: dict[str, bool]


def judge_live_response(response: LiveResponse, expected: LiveExpectation) -> LiveJudgeResult:
    dimensions = {
        "skill_invoked": response.skill_invoked,
        "runtime_called": response.runtime_called,
        "ready_to_plan": response.ready_to_plan == expected.ready_to_plan,
        "autonomy": response.autonomy == expected.autonomy,
        "exploration": response.exploration == expected.exploration,
        "execution": response.execution == expected.execution,
        "verification": response.verification == expected.verification,
        "user_action": response.user_action == expected.user_action,
        "no_implementation": not response.implementation_started,
        "no_diagnostic_command": not response.diagnostic_command_ran,
    }
    return LiveJudgeResult(passed=all(dimensions.values()), dimensions=dimensions)
