from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from trufagent.domain.cartography import GraphQueryResult, GraphState
from trufagent.domain.task import ModelRouting, ModelTier, TaskKind, TaskSignals
from trufagent.experimental.delegation_domain import DelegationPhase, HandoffStatus, PhaseHandoff


class ExplorationDisposition(StrEnum):
    MODEL_FREE = "model-free"
    SHADOW_REQUIRED = "shadow-required"


class ExplorationGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: HandoffStatus
    summary: str
    next_actions: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    disposition: ExplorationDisposition
    handoff: PhaseHandoff | None = None
    reasons: tuple[str, ...] = ()


class GraphifyApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    should_query: bool
    reasons: tuple[str, ...] = ()


def evaluate_graphify_applicability(
    *,
    signals: TaskSignals,
    required_symbols: list[str],
) -> GraphifyApplicability:
    reasons: list[str] = []
    if signals.open_decisions:
        reasons.append("task has open decisions")
    if signals.external_constraint or signals.hypothesis_may_negate_work:
        reasons.append("task requires evidence beyond repository structure")
    if signals.kind in {
        TaskKind.ARCHITECTURE,
        TaskKind.RESEARCH,
        TaskKind.VISUAL_REDESIGN,
    }:
        reasons.append(f"{signals.kind.value} requires model judgment")
    if signals.kind == TaskKind.BUG and signals.cause_known is not True:
        reasons.append("bug cause is not confirmed")
    if signals.kind == TaskKind.FEATURE and not signals.approved_plan:
        reasons.append("feature lacks an approved plan")
    if signals.kind == TaskKind.PLANNED_IMPLEMENTATION and not signals.approved_plan:
        reasons.append("implementation plan is not approved")
    if signals.kind == TaskKind.SMALL_CHANGE and not signals.solution_known:
        reasons.append("small change solution is not known")
    if not required_symbols:
        reasons.append("no required structural symbols were declared")
    return GraphifyApplicability(should_query=not reasons, reasons=tuple(reasons))


def evaluate_graphify_first(
    *,
    signals: TaskSignals,
    graph: GraphQueryResult | None,
    required_symbols: list[str],
) -> ExplorationGateResult:
    applicability = evaluate_graphify_applicability(
        signals=signals,
        required_symbols=required_symbols,
    )
    if not applicability.should_query:
        return ExplorationGateResult(
            status=HandoffStatus.WARNING,
            summary="Graphify intentionally skipped; model judgment is required.",
            next_actions=("Use supervised shadow exploration.",),
            disposition=ExplorationDisposition.SHADOW_REQUIRED,
            reasons=applicability.reasons,
        )
    reasons = list(applicability.reasons)
    if graph is None:
        reasons.append("cartography result is missing")
    else:
        if graph.graph_state != GraphState.FRESH:
            reasons.append("cartography snapshot is not fresh")
        if not graph.nodes:
            reasons.append("cartography returned no nodes")
    searchable = ""
    if graph is not None:
        searchable = "\n".join(
            f"{node.label} {node.source_file or ''}" for node in graph.nodes
        ).casefold()
    missing = [symbol for symbol in required_symbols if symbol.casefold() not in searchable]
    if missing:
        reasons.append(f"missing required symbols: {', '.join(missing)}")
        if graph is not None and graph.truncated:
            reasons.append("cartography result is truncated before target completion")

    if reasons:
        return ExplorationGateResult(
            status=HandoffStatus.WARNING,
            summary="Graphify evidence is insufficient to skip model exploration.",
            next_actions=("Use supervised shadow exploration or refine the graph query.",),
            disposition=ExplorationDisposition.SHADOW_REQUIRED,
            reasons=tuple(reasons),
        )

    matched_nodes = [
        node
        for node in graph.nodes
        if any(
            symbol.casefold() in f"{node.label} {node.source_file or ''}".casefold()
            for symbol in required_symbols
        )
    ]
    artifacts = tuple(dict.fromkeys(node.source_file for node in matched_nodes if node.source_file))
    evidence = tuple(dict.fromkeys(node.label for node in matched_nodes))
    handoff = PhaseHandoff(
        phase=DelegationPhase.EXPLORATION,
        status=HandoffStatus.SUCCESS,
        summary="Fresh target-complete Graphify evidence satisfied structural targets.",
        next_actions=("Continue without a model exploration invocation.",),
        artifacts=artifacts,
        evidence=evidence,
    )
    return ExplorationGateResult(
        status=HandoffStatus.SUCCESS,
        summary="Model exploration skipped: Graphify evidence is sufficient.",
        next_actions=("Compile exploration with tier none.",),
        artifacts=artifacts,
        disposition=ExplorationDisposition.MODEL_FREE,
        handoff=handoff,
    )


def apply_exploration_gate(
    route: ModelRouting,
    gate: ExplorationGateResult,
) -> ModelRouting:
    if gate.disposition != ExplorationDisposition.MODEL_FREE:
        return route
    return route.model_copy(update={"exploration": ModelTier.NONE})
