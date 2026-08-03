from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from trufagent.application.task_extractor import TaskIntake, extract_task_signals
from trufagent.domain.task import (
    AutonomyBoundary,
    EffortLevel,
    TaskMode,
)


class CaseExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: TaskMode
    exploration: EffortLevel
    execution: EffortLevel
    verification: EffortLevel
    autonomy: AutonomyBoundary
    ready: bool
    skills: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    task: str
    expected: CaseExpectation


class EvaluationSuite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(alias="schema")
    name: str
    cases: list[EvaluationCase]


class CaseEvaluation(BaseModel):
    case_id: str
    passed: bool
    dimensions: dict[str, bool]
    expected: CaseExpectation
    actual: CaseExpectation


class EvaluationReport(BaseModel):
    suite: str
    passed: int
    total: int
    pass_rate: float
    dimension_rates: dict[str, float]
    cases: list[CaseEvaluation]


def load_evaluation_suite(path: Path) -> EvaluationSuite:
    return EvaluationSuite.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def evaluate_suite(suite: EvaluationSuite) -> EvaluationReport:
    results: list[CaseEvaluation] = []
    dimension_totals: dict[str, int] = {}
    dimension_passes: dict[str, int] = {}

    for case in suite.cases:
        extraction = extract_task_signals(TaskIntake(task=case.task))
        strategy = extraction.strategy
        actual = CaseExpectation(
            mode=strategy.task_profile.mode,
            exploration=strategy.budgets.exploration,
            execution=strategy.budgets.execution,
            verification=strategy.budgets.verification,
            autonomy=strategy.autonomy_boundary,
            ready=extraction.ready_to_plan,
            skills=strategy.skills,
            evidence=strategy.evidence_required,
        )
        dimensions = {
            "mode": actual.mode == case.expected.mode,
            "exploration": actual.exploration == case.expected.exploration,
            "execution": actual.execution == case.expected.execution,
            "verification": actual.verification == case.expected.verification,
            "autonomy": actual.autonomy == case.expected.autonomy,
            "ready": actual.ready == case.expected.ready,
            "skills": set(case.expected.skills).issubset(actual.skills),
            "evidence": set(case.expected.evidence).issubset(actual.evidence),
        }
        for name, passed in dimensions.items():
            dimension_totals[name] = dimension_totals.get(name, 0) + 1
            dimension_passes[name] = dimension_passes.get(name, 0) + int(passed)
        results.append(
            CaseEvaluation(
                case_id=case.id,
                passed=all(dimensions.values()),
                dimensions=dimensions,
                expected=case.expected,
                actual=actual,
            )
        )

    passed = sum(result.passed for result in results)
    return EvaluationReport(
        suite=suite.name,
        passed=passed,
        total=len(results),
        pass_rate=passed / len(results) if results else 0,
        dimension_rates={
            name: dimension_passes[name] / total for name, total in dimension_totals.items()
        },
        cases=results,
    )
