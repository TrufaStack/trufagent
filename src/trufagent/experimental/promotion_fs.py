from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from pydantic import ValidationError

from trufagent.experimental.codex_shadow_runner import shadow_network_is_default_deny
from trufagent.experimental.context_projection import (
    ContextProjectionError,
    create_context_projection,
)
from trufagent.experimental.pilot_fs import completed_pilot_task_count
from trufagent.experimental.promotion import PromotionFacts, PromotionPolicy
from trufagent.experimental.promotion_review import load_approved_review
from trufagent.experimental.promotion_workspace import (
    load_promotion_workspace,
    operation_gate_is_enforced,
)


class PromotionPolicyError(RuntimeError):
    pass


def _default_policy() -> PromotionPolicy:
    return PromotionPolicy.model_validate(
        {
            "schema": "trufagent.promotion-policy.v1",
            "profile": "pilot",
            "context": {
                "sanitized_projection_required": True,
                "excluded_globs": [
                    ".env*",
                    "*.pem",
                    "*.key",
                    "*credentials*",
                    "*secrets*",
                    "*.dump",
                    "*.sql",
                    "uploads/**",
                    "private-data/**",
                ],
            },
            "external_services": {
                "default_deny": True,
                "blocked_categories": [
                    "production-database",
                    "storage",
                    "crm",
                    "messaging",
                    "email",
                    "deployment",
                ],
            },
            "writes": {
                "mode": "isolated-worktree",
                "human_review_required": True,
                "explicit_apply_confirmation": True,
            },
            "operations": {
                "git_push": "forbidden",
                "deploy": "forbidden",
                "migrations": "forbidden",
                "production_commands": "forbidden",
            },
            "pilot": {"required_tasks": 10, "live_canary_required": True},
        }
    )


def initialize_pilot_policy(project_root: Path) -> Path:
    path = Path(project_root).resolve() / ".trufagent" / "promotion.yaml"
    policy = _default_policy()
    rendered = yaml.safe_dump(
        policy.model_dump(mode="json", by_alias=True),
        sort_keys=False,
        allow_unicode=True,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise PromotionPolicyError(f"promotion policy already differs: {path}")
        return path
    path.write_text(rendered, encoding="utf-8")
    return path


def load_promotion_policy(project_root: Path) -> PromotionPolicy:
    path = Path(project_root).resolve() / ".trufagent" / "promotion.yaml"
    try:
        return PromotionPolicy.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise PromotionPolicyError(f"promotion policy not found: {path}") from exc
    except (OSError, ValidationError, yaml.YAMLError) as exc:
        raise PromotionPolicyError(f"invalid promotion policy: {path}") from exc


def collect_promotion_facts(
    project_root: Path,
    policy: PromotionPolicy,
) -> PromotionFacts:
    projection_verified = False
    try:
        with TemporaryDirectory(prefix="trufagent-promotion-check-") as temporary:
            create_context_projection(
                project_root,
                Path(temporary) / "project",
                policy.context,
            )
            projection_verified = True
    except (ContextProjectionError, OSError):
        projection_verified = False
    workspace = load_promotion_workspace(project_root)
    approved_review = load_approved_review(project_root)
    return PromotionFacts(
        sanitized_context_projection=projection_verified,
        network_default_deny=shadow_network_is_default_deny(),
        isolated_write_worktree=workspace is not None,
        human_apply_review=approved_review is not None,
        git_deploy_migration_gate=operation_gate_is_enforced(project_root),
        completed_pilot_tasks=completed_pilot_task_count(project_root),
    )
