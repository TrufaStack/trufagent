from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from trufagent.application.context_builder import ContextBuilder, ContextRequest
from trufagent.application.coordinator_gate import (
    CoordinatorGateResult,
    apply_coordinator_gate,
    evaluate_host_coordinator,
)
from trufagent.application.exploration_gate import (
    ExplorationGateResult,
    apply_exploration_gate,
    evaluate_graphify_applicability,
    evaluate_graphify_first,
)
from trufagent.application.model_routing import route_models
from trufagent.application.skill_catalog import (
    InMemorySkillCatalog,
    SkillDescriptor,
)
from trufagent.application.task_classifier import classify_task
from trufagent.domain.context import ContextPacket
from trufagent.domain.memory import MemoryKind
from trufagent.domain.task import (
    AutonomyBoundary,
    ContextSelection,
    ModelRouting,
    TaskKind,
    TaskSignals,
    TaskStrategy,
)
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository


class PlanTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str = Field(min_length=1)
    project: str = Field(min_length=1)
    project_root: Path
    signals: TaskSignals
    include_user_memory: bool = False
    memory_token_budget: int = Field(default=2_000, ge=64)
    cartography_token_budget: int = Field(default=1_000, ge=64)
    use_skills: list[str] = Field(default_factory=list)
    without_skills: list[str] = Field(default_factory=list)
    required_symbols: list[str] = Field(default_factory=list)


class TaskPlan(BaseModel):
    strategy: TaskStrategy
    context: ContextPacket
    selected_skills: list[SkillDescriptor] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str
    model_route: ModelRouting
    coordinator_gate: CoordinatorGateResult
    exploration_gate: ExplorationGateResult | None = None


def _context_selection(packet: ContextPacket) -> ContextSelection:
    by_kind: dict[MemoryKind, list[str]] = {}
    for item in packet.items:
        by_kind.setdefault(item.kind, []).append(item.memory_id)
    structural_targets = (
        list(dict.fromkeys(node.label for node in packet.cartography.nodes))
        if packet.cartography
        else []
    )
    return ContextSelection(
        rules=by_kind.get(MemoryKind.RULE, []),
        decisions=by_kind.get(MemoryKind.DECISION, [])
        + by_kind.get(MemoryKind.NEGATIVE_DECISION, []),
        risks=by_kind.get(MemoryKind.RISK, []),
        artifacts=by_kind.get(MemoryKind.EXTERNAL_ARTIFACT, []),
        structural_targets=structural_targets,
    )


def _requires_cartography(signals: TaskSignals) -> bool:
    return (
        signals.kind == TaskKind.ARCHITECTURE
        or signals.persistence
        or signals.shared_contract
        or signals.multi_surface
    )


class PlanTaskService:
    def __init__(
        self,
        repository: MarkdownMemoryRepository,
        *,
        cartography,
        skills: InMemorySkillCatalog,
    ) -> None:
        self.context_builder = ContextBuilder(repository, cartography=cartography)
        self.skills = skills

    def plan(self, request: PlanTaskRequest) -> TaskPlan:
        strategy = classify_task(request.signals)
        context_query = request.task
        cartography_query = (
            "\n".join(request.required_symbols) if request.required_symbols else None
        )
        graphify_applicability = evaluate_graphify_applicability(
            signals=request.signals,
            required_symbols=request.required_symbols,
        )
        context = self.context_builder.build(
            ContextRequest(
                query=context_query,
                cartography_query=cartography_query,
                project=request.project,
                project_root=request.project_root,
                include_user=request.include_user_memory,
                token_budget=request.memory_token_budget,
                cartography_token_budget=request.cartography_token_budget,
                query_cartography=(
                    graphify_applicability.should_query
                    or _requires_cartography(request.signals)
                    or bool(request.required_symbols)
                ),
            )
        )
        warnings = list(context.warnings)

        requested_skills = [
            name
            for name in strategy.skills + request.use_skills
            if name not in set(request.without_skills)
        ]
        skill_selection = self.skills.select(requested_skills)
        warnings.extend(skill_selection.warnings)

        evidence = list(strategy.evidence_required)
        autonomy = strategy.autonomy_boundary
        cartography_failed = context.cartography is None and any(
            "cartography" in warning or "graph" in warning for warning in context.warnings
        )
        if (
            cartography_failed
            and _requires_cartography(request.signals)
            and graphify_applicability.should_query
        ):
            autonomy = AutonomyBoundary.BLOCK
            evidence.append("refresh-cartography")

        selected_names = [skill.name for skill in skill_selection.selected]
        strategy = strategy.model_copy(
            update={
                "context": _context_selection(context),
                "skills": selected_names,
                "evidence_required": list(dict.fromkeys(evidence)),
                "autonomy_boundary": autonomy,
            }
        )
        budgets = strategy.budgets
        summary = (
            f"{strategy.task_profile.mode.value}; effort "
            f"E={budgets.exploration.value}/X={budgets.execution.value}/"
            f"V={budgets.verification.value}; autonomy={autonomy.value}"
        )
        model_route = route_models(strategy)
        coordinator_gate = evaluate_host_coordinator(strategy)
        model_route = apply_coordinator_gate(model_route, coordinator_gate)
        exploration_gate = None
        if request.required_symbols:
            exploration_gate = evaluate_graphify_first(
                signals=request.signals,
                graph=context.cartography,
                required_symbols=request.required_symbols,
            )
            model_route = apply_exploration_gate(model_route, exploration_gate)
        return TaskPlan(
            strategy=strategy,
            context=context,
            selected_skills=skill_selection.selected,
            warnings=warnings,
            summary=summary,
            model_route=model_route,
            coordinator_gate=coordinator_gate,
            exploration_gate=exploration_gate,
        )
