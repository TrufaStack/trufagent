from __future__ import annotations

from dataclasses import dataclass

from trufagent.domain.task import (
    AutonomyBoundary,
    EffortBudgets,
    EffortLevel,
    Level,
    Reversibility,
    RiskLevel,
    TaskKind,
    TaskMode,
    TaskProfile,
    TaskSignals,
    TaskStrategy,
)


@dataclass(frozen=True)
class _BaseStrategy:
    mode: TaskMode
    ambiguity: Level
    risk: RiskLevel
    reversibility: Reversibility
    exploration: EffortLevel
    execution: EffortLevel
    verification: EffortLevel


_BASES = {
    TaskKind.SMALL_CHANGE: _BaseStrategy(
        TaskMode.EXECUTION_DRIVEN,
        Level.LOW,
        RiskLevel.LOW,
        Reversibility.EASY,
        EffortLevel.LOW,
        EffortLevel.LOW,
        EffortLevel.LOW,
    ),
    TaskKind.BUG: _BaseStrategy(
        TaskMode.DISCOVERY_DRIVEN,
        Level.HIGH,
        RiskLevel.MEDIUM,
        Reversibility.MODERATE,
        EffortLevel.HIGH,
        EffortLevel.MEDIUM,
        EffortLevel.HIGH,
    ),
    TaskKind.FEATURE: _BaseStrategy(
        TaskMode.EXECUTION_DRIVEN,
        Level.MEDIUM,
        RiskLevel.MEDIUM,
        Reversibility.MODERATE,
        EffortLevel.LOW,
        EffortLevel.MEDIUM,
        EffortLevel.MEDIUM,
    ),
    TaskKind.ARCHITECTURE: _BaseStrategy(
        TaskMode.MIXED,
        Level.HIGH,
        RiskLevel.HIGH,
        Reversibility.HARD,
        EffortLevel.HIGH,
        EffortLevel.MEDIUM,
        EffortLevel.HIGH,
    ),
    TaskKind.DIAGNOSTIC: _BaseStrategy(
        TaskMode.DISCOVERY_DRIVEN,
        Level.MEDIUM,
        RiskLevel.MEDIUM,
        Reversibility.EASY,
        EffortLevel.MEDIUM,
        EffortLevel.LOW,
        EffortLevel.MEDIUM,
    ),
    TaskKind.VISUAL_REDESIGN: _BaseStrategy(
        TaskMode.DISCOVERY_DRIVEN,
        Level.HIGH,
        RiskLevel.MEDIUM,
        Reversibility.MODERATE,
        EffortLevel.HIGH,
        EffortLevel.HIGH,
        EffortLevel.HIGH,
    ),
    TaskKind.RESEARCH: _BaseStrategy(
        TaskMode.DISCOVERY_DRIVEN,
        Level.HIGH,
        RiskLevel.LOW,
        Reversibility.EASY,
        EffortLevel.HIGH,
        EffortLevel.NONE,
        EffortLevel.MEDIUM,
    ),
    TaskKind.PLANNED_IMPLEMENTATION: _BaseStrategy(
        TaskMode.EXECUTION_DRIVEN,
        Level.LOW,
        RiskLevel.MEDIUM,
        Reversibility.MODERATE,
        EffortLevel.LOW,
        EffortLevel.HIGH,
        EffortLevel.HIGH,
    ),
}

_ORDER = {
    EffortLevel.NONE: 0,
    EffortLevel.LOW: 1,
    EffortLevel.MEDIUM: 2,
    EffortLevel.HIGH: 3,
    EffortLevel.CRITICAL: 4,
}


def _max_effort(current: EffortLevel, required: EffortLevel) -> EffortLevel:
    return required if _ORDER[required] > _ORDER[current] else current


def classify_task(signals: TaskSignals) -> TaskStrategy:
    base = _BASES[signals.kind]
    mode = base.mode
    ambiguity = base.ambiguity
    risk = base.risk
    reversibility = base.reversibility
    exploration = base.exploration
    execution = base.execution
    verification = base.verification
    reasons = [f"task-kind:{signals.kind.value}"]
    evidence: list[str] = []
    skills: list[str] = []
    autonomy = AutonomyBoundary.PROCEED

    if signals.kind == TaskKind.BUG:
        if signals.cause_known is False:
            reasons.append("unknown-cause")
            skills.append("systematic-debugging")
        if signals.localized and signals.library_behavior and not signals.multi_surface:
            mode = TaskMode.MIXED
            ambiguity = Level.MEDIUM
            exploration = EffortLevel.MEDIUM
            execution = EffortLevel.LOW
            verification = EffortLevel.MEDIUM
            reasons.append("localized-library-behavior")
        evidence.append("reproduction-and-root-cause")

    if signals.open_decisions:
        mode = TaskMode.MIXED
        exploration = _max_effort(exploration, EffortLevel.MEDIUM)
        skills.append("brainstorming")
        reasons.append("open-decisions")

    if signals.approved_plan:
        mode = TaskMode.EXECUTION_DRIVEN
        reasons.append("approved-plan")
        evidence.append("plan-completion")

    if signals.integration_testing and not signals.solution_known:
        exploration = _max_effort(exploration, EffortLevel.MEDIUM)
        reasons.append("integration-discovery")

    if signals.persistence:
        risk = RiskLevel.HIGH
        verification = _max_effort(verification, EffortLevel.HIGH)
        evidence.append("persistence-regression")
        reasons.append("persistence-risk")
        autonomy = AutonomyBoundary.ANNOUNCE

    if signals.shared_contract:
        exploration = _max_effort(exploration, EffortLevel.HIGH)
        verification = _max_effort(verification, EffortLevel.HIGH)
        evidence.append("consumer-impact-search")
        reasons.append("shared-contract-impact")

    if signals.multi_surface:
        if signals.kind != TaskKind.SMALL_CHANGE:
            verification = _max_effort(verification, EffortLevel.HIGH)
        evidence.append("all-surfaces-verified")
        reasons.append("multi-surface")

    if signals.shared_symptom:
        exploration = _max_effort(exploration, EffortLevel.HIGH)
        reasons.append("shared-symptom-separate-traces")

    if signals.permissions:
        risk = RiskLevel.HIGH
        verification = _max_effort(verification, EffortLevel.HIGH)
        evidence.append("permission-matrix")
        reasons.append("permission-risk")
        autonomy = AutonomyBoundary.ANNOUNCE

    if signals.state_logic:
        verification = _max_effort(verification, EffortLevel.HIGH)
        evidence.append("state-matrix-tests")
        reasons.append("state-logic")

    if signals.visual or signals.kind == TaskKind.VISUAL_REDESIGN:
        evidence.append("rendered-visual-comparison")
        reasons.append("visual-evidence")

    if signals.approved_artifact and not signals.artifact_available:
        exploration = EffortLevel.HIGH
        verification = _max_effort(verification, EffortLevel.HIGH)
        evidence.append("obtain-approved-artifact")
        reasons.append("approved-artifact-missing")
        autonomy = AutonomyBoundary.BLOCK

    if signals.external_constraint:
        evidence.append("external-constraint-validated")
        reasons.append("external-constraint")

    if signals.hypothesis_may_negate_work:
        execution = EffortLevel.NONE
        evidence.append("hypothesis-validation")
        reasons.append("no-build-is-valid")

    if signals.production:
        risk = RiskLevel.CRITICAL
        verification = EffortLevel.CRITICAL
        evidence.append("production-safe-verification")
        reasons.append("production-risk")
        autonomy = AutonomyBoundary.CONFIRM

    if signals.secrets:
        risk = RiskLevel.CRITICAL
        verification = EffortLevel.CRITICAL
        evidence.append("secret-safe-diagnostics")
        reasons.append("secret-exposure-risk")
        if autonomy != AutonomyBoundary.BLOCK:
            autonomy = AutonomyBoundary.CONFIRM

    return TaskStrategy(
        task_profile=TaskProfile(
            mode=mode,
            ambiguity=ambiguity,
            risk=risk,
            reversibility=reversibility,
        ),
        budgets=EffortBudgets(
            exploration=exploration,
            execution=execution,
            verification=verification,
        ),
        skills=list(dict.fromkeys(skills)),
        evidence_required=list(dict.fromkeys(evidence)),
        autonomy_boundary=autonomy,
        reasons=reasons,
    )
