from __future__ import annotations

import difflib
import hashlib
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from trufagent.experimental.promotion_workspace import (
    load_promotion_workspace,
)
from trufagent.infrastructure.memory_markdown import find_secret_shapes
from trufagent.infrastructure.worktree_fingerprint import fingerprint_worktree


class PromotionReviewError(RuntimeError):
    pass


class PromotionReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.promotion-review\.v1$")
    review_id: str = Field(pattern=r"^rev_[0-9a-f]{16}$")
    workspace_id: str = Field(pattern=r"^wrk_[0-9a-f]{16}$")
    created_at: datetime
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    patch_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    changed_files: int = Field(ge=1)
    patch_path: Path
    approved: bool = False
    apply_allowed: bool = False


def _review_dir(project_root: Path) -> Path:
    return Path(project_root).resolve() / ".trufagent" / "state" / "promotion-reviews"


def _safe_text(path: Path) -> str:
    if path.is_symlink():
        raise PromotionReviewError("review rejects symlinks")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise PromotionReviewError("review rejects binary changes") from exc
    if find_secret_shapes(text):
        raise PromotionReviewError("review rejects secret-shaped content")
    return text


def create_promotion_review(project_root: Path) -> PromotionReview:
    source = Path(project_root).resolve()
    workspace = load_promotion_workspace(source)
    if workspace is None:
        raise PromotionReviewError("promotion workspace evidence is missing")
    if fingerprint_worktree(source) != workspace.source_fingerprint:
        raise PromotionReviewError("source changed after workspace preparation")
    baseline = json.loads(
        (workspace.workspace_root.parent / "baseline.json").read_text(encoding="utf-8")
    )
    if not isinstance(baseline, dict) or not all(
        isinstance(path, str) and isinstance(digest, str)
        for path, digest in baseline.items()
    ):
        raise PromotionReviewError("invalid workspace baseline")

    current = {
        path.relative_to(workspace.workspace_root).as_posix(): path
        for path in workspace.workspace_root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    changed = []
    patch_lines: list[str] = []
    for relative in sorted(set(baseline) | set(current)):
        candidate = current.get(relative)
        if candidate is None:
            before = _safe_text(source / relative)
            after = ""
        else:
            after = _safe_text(candidate)
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if baseline.get(relative) == digest:
                continue
            before = _safe_text(source / relative) if relative in baseline else ""
        changed.append(relative)
        patch_lines.extend(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
            )
        )
    if not changed:
        raise PromotionReviewError("workspace contains no reviewable changes")
    patch = "".join(patch_lines)
    review_id = f"rev_{secrets.token_hex(8)}"
    review_dir = _review_dir(source)
    review_dir.mkdir(parents=True, exist_ok=True)
    patch_path = review_dir / f"{review_id}.patch"
    patch_path.write_text(patch, encoding="utf-8")
    review = PromotionReview(
        schema="trufagent.promotion-review.v1",
        review_id=review_id,
        workspace_id=workspace.workspace_id,
        created_at=datetime.now(UTC),
        source_fingerprint=workspace.source_fingerprint,
        patch_digest=hashlib.sha256(patch.encode()).hexdigest(),
        changed_files=len(changed),
        patch_path=patch_path,
    )
    (review_dir / f"{review_id}.json").write_text(
        review.model_dump_json(by_alias=True, indent=2) + "\n"
    )
    return review


def approve_promotion_review(project_root: Path, review_id: str) -> PromotionReview:
    source = Path(project_root).resolve()
    path = _review_dir(source) / f"{review_id}.json"
    try:
        review = PromotionReview.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PromotionReviewError("promotion review not found or invalid") from exc
    workspace = load_promotion_workspace(source)
    if workspace is None or workspace.workspace_id != review.workspace_id:
        raise PromotionReviewError("review does not match the active workspace")
    if fingerprint_worktree(source) != review.source_fingerprint:
        raise PromotionReviewError("source changed after review creation")
    patch = review.patch_path.read_text(encoding="utf-8")
    if hashlib.sha256(patch.encode()).hexdigest() != review.patch_digest:
        raise PromotionReviewError("review patch changed after creation")
    approved = review.model_copy(update={"approved": True})
    path.write_text(approved.model_dump_json(by_alias=True, indent=2) + "\n")
    return approved


def load_approved_review(project_root: Path) -> PromotionReview | None:
    workspace = load_promotion_workspace(project_root)
    if workspace is None:
        return None
    review_dir = _review_dir(project_root)
    for path in sorted(review_dir.glob("rev_*.json"), reverse=True):
        try:
            review = PromotionReview.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if review.workspace_id == workspace.workspace_id and review.approved:
            return review
    return None
