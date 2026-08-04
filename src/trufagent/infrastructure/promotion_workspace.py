from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from trufagent.application.promotion import PromotionPolicy
from trufagent.experimental.context_projection import create_context_projection
from trufagent.infrastructure.worktree_fingerprint import fingerprint_worktree


class PromotionWorkspaceError(RuntimeError):
    pass


class PromotionWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.promotion-workspace\.v1$")
    workspace_id: str = Field(pattern=r"^wrk_[0-9a-f]{16}$")
    created_at: datetime
    source_root_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    workspace_root: Path
    copied_files: int = Field(ge=0)
    excluded_files: int = Field(ge=0)
    quarantined_files: int = Field(ge=0)
    symlinks_rejected: int = Field(ge=0)
    source_write_allowed: bool = False
    apply_allowed: bool = False


class ExecutionBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.execution-boundary\.v1$")
    mode: str = Field(pattern=r"^structured-patch-only$")
    model_shell_allowed: bool = False
    source_write_allowed: bool = False
    source_git_metadata_available: bool = False
    network_allowed: bool = False
    forbidden_operations: tuple[str, ...]


def _state_path(project_root: Path) -> Path:
    return Path(project_root).resolve() / ".trufagent" / "state" / "promotion-workspace.json"


def prepare_promotion_workspace(
    project_root: Path,
    policy: PromotionPolicy,
    *,
    workspace_base: Path = Path("/tmp/trufagent-workspaces"),
) -> PromotionWorkspace:
    source = Path(project_root).resolve()
    workspace_id = f"wrk_{secrets.token_hex(8)}"
    workspace_root = Path(workspace_base).resolve() / workspace_id / "project"
    if workspace_root.exists():
        raise PromotionWorkspaceError("generated workspace already exists")
    manifest = create_context_projection(source, workspace_root, policy.context)
    baseline = {
        path.relative_to(workspace_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in workspace_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    baseline_path = workspace_root.parent / "baseline.json"
    baseline_path.write_text(json.dumps(baseline, sort_keys=True) + "\n")
    boundary = ExecutionBoundary(
        schema="trufagent.execution-boundary.v1",
        mode="structured-patch-only",
        forbidden_operations=(
            "git-push",
            "deploy",
            "migration",
            "production-command",
        ),
    )
    (workspace_root.parent / "execution-boundary.json").write_text(
        boundary.model_dump_json(by_alias=True, indent=2) + "\n"
    )
    record = PromotionWorkspace(
        schema="trufagent.promotion-workspace.v1",
        workspace_id=workspace_id,
        created_at=datetime.now(UTC),
        source_root_digest=hashlib.sha256(str(source).encode()).hexdigest(),
        source_fingerprint=fingerprint_worktree(source),
        workspace_root=workspace_root,
        copied_files=manifest.copied_files,
        excluded_files=manifest.excluded_files,
        quarantined_files=manifest.rejected_secret_files,
        symlinks_rejected=manifest.rejected_symlinks,
    )
    state_path = _state_path(source)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(record.model_dump_json(by_alias=True, indent=2) + "\n")
    return record


def load_promotion_workspace(project_root: Path) -> PromotionWorkspace | None:
    path = _state_path(project_root)
    try:
        record = PromotionWorkspace.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise PromotionWorkspaceError("invalid promotion workspace evidence") from exc
    source = Path(project_root).resolve()
    if record.source_root_digest != hashlib.sha256(str(source).encode()).hexdigest():
        raise PromotionWorkspaceError("promotion workspace belongs to another source root")
    if not record.workspace_root.is_dir():
        raise PromotionWorkspaceError("promotion workspace no longer exists")
    if not (record.workspace_root.parent / "baseline.json").is_file():
        raise PromotionWorkspaceError("promotion workspace baseline no longer exists")
    return record


def operation_gate_is_enforced(project_root: Path) -> bool:
    try:
        workspace = load_promotion_workspace(project_root)
        if workspace is None:
            return False
        boundary = ExecutionBoundary.model_validate_json(
            (workspace.workspace_root.parent / "execution-boundary.json").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, ValueError, PromotionWorkspaceError):
        return False
    required = {"git-push", "deploy", "migration", "production-command"}
    return (
        boundary.mode == "structured-patch-only"
        and not boundary.model_shell_allowed
        and not boundary.source_write_allowed
        and not boundary.source_git_metadata_available
        and not boundary.network_allowed
        and required.issubset(boundary.forbidden_operations)
        and not (workspace.workspace_root / ".git").exists()
        and not workspace.source_write_allowed
        and not workspace.apply_allowed
    )
