from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContextProjectionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sanitized_projection_required: bool = True
    excluded_globs: tuple[str, ...]


class ExternalServicesPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    default_deny: bool = True
    blocked_categories: tuple[str, ...]


class WritePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["isolated-worktree"] = "isolated-worktree"
    human_review_required: bool = True
    explicit_apply_confirmation: bool = True


class OperationsPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    git_push: Literal["forbidden"] = "forbidden"
    deploy: Literal["forbidden"] = "forbidden"
    migrations: Literal["forbidden"] = "forbidden"
    production_commands: Literal["forbidden"] = "forbidden"


class PilotRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    required_tasks: int = Field(default=10, ge=10)
    live_canary_required: bool = True


class PromotionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.promotion-policy\.v1$")
    profile: Literal["pilot"] = "pilot"
    context: ContextProjectionPolicy
    external_services: ExternalServicesPolicy
    writes: WritePolicy
    operations: OperationsPolicy
    pilot: PilotRequirements


class PromotionFacts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sanitized_context_projection: bool = False
    network_default_deny: bool = False
    isolated_write_worktree: bool = False
    human_apply_review: bool = False
    git_deploy_migration_gate: bool = False
    live_canary_passed: bool = False
    completed_pilot_tasks: int = Field(default=0, ge=0)


class PromotionReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.promotion-readiness\.v1$")
    status: Literal["ready", "blocked"]
    summary: str
    next_actions: tuple[str, ...]
    artifacts: tuple[str, ...] = ()
    ready: bool
    checks: dict[str, bool]
    missing: tuple[str, ...]


def evaluate_promotion_readiness(
    policy: PromotionPolicy,
    facts: PromotionFacts,
) -> PromotionReadiness:
    checks = {
        "sanitized-context-projection": (
            policy.context.sanitized_projection_required
            and facts.sanitized_context_projection
        ),
        "network-default-deny": (
            policy.external_services.default_deny and facts.network_default_deny
        ),
        "isolated-write-worktree": (
            policy.writes.mode == "isolated-worktree" and facts.isolated_write_worktree
        ),
        "human-apply-review": (
            policy.writes.human_review_required and facts.human_apply_review
        ),
        "git-deploy-migration-gate": facts.git_deploy_migration_gate,
        "live-canary": (not policy.pilot.live_canary_required or facts.live_canary_passed),
        "ten-task-pilot": facts.completed_pilot_tasks >= policy.pilot.required_tasks,
    }
    missing = tuple(name for name, passed in checks.items() if not passed)
    ready = not missing
    return PromotionReadiness(
        schema="trufagent.promotion-readiness.v1",
        status="ready" if ready else "blocked",
        summary=(
            "Promotion controls are satisfied."
            if ready
            else "Promotion is blocked until every runtime control has evidence."
        ),
        next_actions=(
            ("Keep the readiness evidence with the promotion record.",)
            if ready
            else tuple(f"Implement or verify {name}." for name in missing)
        ),
        ready=ready,
        checks=checks,
        missing=missing,
    )
