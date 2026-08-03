from __future__ import annotations

from trufagent.domain.task import (
    EffortLevel,
    ModelRouting,
    ModelTier,
    TaskStrategy,
)

_TIER_BY_EFFORT = {
    EffortLevel.NONE: ModelTier.NONE,
    EffortLevel.LOW: ModelTier.ECONOMY,
    EffortLevel.MEDIUM: ModelTier.BALANCED,
    EffortLevel.HIGH: ModelTier.FRONTIER,
    EffortLevel.CRITICAL: ModelTier.FRONTIER,
}


def route_models(strategy: TaskStrategy) -> ModelRouting:
    budgets = strategy.budgets
    return ModelRouting(
        coordinator=ModelTier.ECONOMY,
        exploration=_TIER_BY_EFFORT[budgets.exploration],
        execution=_TIER_BY_EFFORT[budgets.execution],
        verification=_TIER_BY_EFFORT[budgets.verification],
    )
