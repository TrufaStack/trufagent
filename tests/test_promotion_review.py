from pathlib import Path

import pytest

from trufagent.infrastructure.promotion_fs import (
    collect_promotion_facts,
    initialize_pilot_policy,
    load_promotion_policy,
)
from trufagent.infrastructure.promotion_review import (
    PromotionReviewError,
    approve_promotion_review,
    create_promotion_review,
)
from trufagent.infrastructure.promotion_workspace import prepare_promotion_workspace


def _workspace(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("VALUE = 1\n")
    initialize_pilot_policy(source)
    policy = load_promotion_policy(source)
    workspace = prepare_promotion_workspace(
        source,
        policy,
        workspace_base=tmp_path / "workspaces",
    )
    return source, policy, workspace


def test_review_is_sealed_and_requires_exact_explicit_approval(tmp_path: Path) -> None:
    source, policy, workspace = _workspace(tmp_path)
    (workspace.workspace_root / "app.py").write_text("VALUE = 2\n")

    review = create_promotion_review(source)

    assert review.approved is False
    assert review.apply_allowed is False
    assert "-VALUE = 1" in review.patch_path.read_text()
    assert "+VALUE = 2" in review.patch_path.read_text()
    assert collect_promotion_facts(source, policy).human_apply_review is False

    with pytest.raises(PromotionReviewError):
        approve_promotion_review(source, "rev_0000000000000000")

    approved = approve_promotion_review(source, review.review_id)
    assert approved.approved is True
    assert approved.apply_allowed is False
    assert collect_promotion_facts(source, policy).human_apply_review is True


def test_review_fails_if_source_changed_after_workspace_creation(tmp_path: Path) -> None:
    source, _, workspace = _workspace(tmp_path)
    (workspace.workspace_root / "app.py").write_text("VALUE = 2\n")
    (source / "app.py").write_text("VALUE = 3\n")

    with pytest.raises(PromotionReviewError, match="source changed"):
        create_promotion_review(source)


def test_approval_fails_if_sealed_patch_was_modified(tmp_path: Path) -> None:
    source, _, workspace = _workspace(tmp_path)
    (workspace.workspace_root / "app.py").write_text("VALUE = 2\n")
    review = create_promotion_review(source)
    review.patch_path.write_text("tampered\n")

    with pytest.raises(PromotionReviewError, match="patch changed"):
        approve_promotion_review(source, review.review_id)
