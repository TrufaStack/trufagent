from pathlib import Path

from trufagent.application.promotion import (
    PromotionFacts,
    evaluate_promotion_readiness,
)
from trufagent.infrastructure.promotion_fs import (
    collect_promotion_facts,
    initialize_pilot_policy,
    load_promotion_policy,
)


def test_default_pilot_policy_is_generic_and_fail_closed(tmp_path: Path) -> None:
    path = initialize_pilot_policy(tmp_path)
    policy = load_promotion_policy(tmp_path)

    assert path == tmp_path / ".trufagent" / "promotion.yaml"
    assert policy.profile == "pilot"
    assert policy.context.sanitized_projection_required is True
    assert ".env*" in policy.context.excluded_globs
    assert policy.external_services.default_deny is True
    assert policy.writes.mode == "isolated-worktree"
    assert policy.writes.human_review_required is True
    assert policy.operations.git_push == "forbidden"
    assert policy.operations.deploy == "forbidden"
    assert policy.operations.migrations == "forbidden"
    assert policy.pilot.required_tasks == 10
    rendered = path.read_text()
    assert "JCT" not in rendered
    assert "Zoho" not in rendered


def test_collect_promotion_facts_verifies_sanitized_projection(tmp_path: Path) -> None:
    (tmp_path / "safe.py").write_text("SAFE = True\n")
    (tmp_path / ".env.local").write_text("SECRET=excluded\n")
    initialize_pilot_policy(tmp_path)
    policy = load_promotion_policy(tmp_path)

    facts = collect_promotion_facts(tmp_path, policy)

    assert facts.sanitized_context_projection is True
    assert facts.network_default_deny is True


def test_readiness_requires_runtime_evidence_not_policy_declarations(
    tmp_path: Path,
) -> None:
    initialize_pilot_policy(tmp_path)
    policy = load_promotion_policy(tmp_path)

    blocked = evaluate_promotion_readiness(policy, PromotionFacts())

    assert blocked.status == "blocked"
    assert blocked.ready is False
    assert "sanitized-context-projection" in blocked.missing
    assert "ten-task-pilot" in blocked.missing

    ready = evaluate_promotion_readiness(
        policy,
        PromotionFacts(
            sanitized_context_projection=True,
            network_default_deny=True,
            isolated_write_worktree=True,
            human_apply_review=True,
            git_deploy_migration_gate=True,
            live_canary_passed=True,
            completed_pilot_tasks=10,
        ),
    )

    assert ready.status == "ready"
    assert ready.ready is True
    assert ready.missing == ()
