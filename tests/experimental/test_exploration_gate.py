from trufagent.domain.cartography import (
    GraphQueryResult,
    GraphReference,
    GraphState,
)
from trufagent.domain.task import ModelRouting, ModelTier, TaskKind, TaskSignals
from trufagent.experimental.exploration_gate import (
    ExplorationDisposition,
    apply_exploration_gate,
    evaluate_graphify_applicability,
    evaluate_graphify_first,
)


def _graph(*, truncated: bool = False) -> GraphQueryResult:
    return GraphQueryResult(
        summary="structural path",
        nodes=[
            GraphReference(
                node_id="load_model_overrides",
                label="load_model_overrides()",
                source_file="src/trufagent/infrastructure/model_profiles.py",
            ),
            GraphReference(
                node_id="compile_delegation_protocol",
                label="compile_delegation_protocol()",
                source_file="src/trufagent/application/delegation.py",
            ),
        ],
        graphify_version="0.9.30",
        graph_state=GraphState.FRESH,
        truncated=truncated,
    )


def test_fresh_complete_structural_evidence_skips_model() -> None:
    gate = evaluate_graphify_first(
        signals=TaskSignals(
            kind=TaskKind.SMALL_CHANGE,
            solution_known=True,
            localized=True,
        ),
        graph=_graph(),
        required_symbols=["load_model_overrides", "compile_delegation_protocol"],
    )

    assert gate.disposition == ExplorationDisposition.MODEL_FREE
    assert gate.handoff is not None
    assert gate.artifacts == (
        "src/trufagent/infrastructure/model_profiles.py",
        "src/trufagent/application/delegation.py",
    )
    route = ModelRouting(
        coordinator=ModelTier.ECONOMY,
        exploration=ModelTier.BALANCED,
        execution=ModelTier.ECONOMY,
        verification=ModelTier.FRONTIER,
    )
    assert apply_exploration_gate(route, gate).exploration == ModelTier.NONE


def test_unknown_bug_cause_never_uses_structural_shortcut() -> None:
    gate = evaluate_graphify_first(
        signals=TaskSignals(kind=TaskKind.BUG, cause_known=False),
        graph=_graph(),
        required_symbols=["load_model_overrides"],
    )

    assert gate.disposition == ExplorationDisposition.SHADOW_REQUIRED
    assert gate.reasons == ("bug cause is not confirmed",)
    assert gate.summary == "Graphify intentionally skipped; model judgment is required."


def test_truncated_graph_is_allowed_only_when_declared_targets_are_complete() -> None:
    truncated = evaluate_graphify_first(
        signals=TaskSignals(kind=TaskKind.SMALL_CHANGE, solution_known=True),
        graph=_graph(truncated=True),
        required_symbols=["load_model_overrides"],
    )
    missing = evaluate_graphify_first(
        signals=TaskSignals(kind=TaskKind.SMALL_CHANGE, solution_known=True),
        graph=_graph(),
        required_symbols=["unknown_symbol"],
    )

    assert truncated.disposition == ExplorationDisposition.MODEL_FREE
    assert missing.disposition == ExplorationDisposition.SHADOW_REQUIRED
    assert "missing required symbols: unknown_symbol" in missing.reasons
    missing_from_truncated = evaluate_graphify_first(
        signals=TaskSignals(kind=TaskKind.SMALL_CHANGE, solution_known=True),
        graph=_graph(truncated=True),
        required_symbols=["unknown_symbol"],
    )
    assert (
        "cartography result is truncated before target completion" in missing_from_truncated.reasons
    )


def test_no_declared_symbols_cannot_skip_model() -> None:
    gate = evaluate_graphify_first(
        signals=TaskSignals(kind=TaskKind.SMALL_CHANGE, solution_known=True),
        graph=_graph(),
        required_symbols=[],
    )

    assert gate.disposition == ExplorationDisposition.SHADOW_REQUIRED


def test_ineligible_task_abstains_before_graph_query() -> None:
    applicability = evaluate_graphify_applicability(
        signals=TaskSignals(
            kind=TaskKind.ARCHITECTURE,
            open_decisions=True,
        ),
        required_symbols=["compile_delegation_protocol"],
    )

    assert applicability.should_query is False
    assert applicability.reasons == (
        "task has open decisions",
        "architecture requires model judgment",
    )


def test_known_structural_task_is_eligible_for_graph_query() -> None:
    applicability = evaluate_graphify_applicability(
        signals=TaskSignals(
            kind=TaskKind.BUG,
            cause_known=True,
            localized=True,
        ),
        required_symbols=["compile_delegation_protocol"],
    )

    assert applicability.should_query is True
    assert applicability.reasons == ()
