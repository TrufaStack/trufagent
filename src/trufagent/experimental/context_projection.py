from __future__ import annotations

import fnmatch
import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from trufagent.experimental.promotion import ContextProjectionPolicy
from trufagent.infrastructure.memory_markdown import find_secret_shapes


class ContextProjectionError(RuntimeError):
    pass


class ProjectionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.context-projection\.v1$")
    copied_files: int = Field(ge=0)
    excluded_files: int = Field(ge=0)
    rejected_secret_files: int = Field(ge=0)
    rejected_symlinks: int = Field(ge=0)


_ALWAYS_EXCLUDED = (
    ".git/**",
    ".trufagent/**",
    ".next/**",
    ".nuxt/**",
    ".pytest_cache/**",
    ".ruff_cache/**",
    "__pycache__/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    "coverage/**",
)


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    name = Path(path).name
    return any(
        fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(name, pattern)
        for pattern in patterns
    )


def create_context_projection(
    project_root: Path,
    destination: Path,
    policy: ContextProjectionPolicy,
) -> ProjectionManifest:
    root = Path(project_root).resolve()
    target = Path(destination).resolve()
    if target == root or root in target.parents:
        raise ContextProjectionError("projection destination must be outside the source project")
    target.mkdir(parents=True, exist_ok=False)

    copied = excluded = rejected_secrets = rejected_symlinks = 0
    patterns = _ALWAYS_EXCLUDED + policy.excluded_globs
    for source in root.rglob("*"):
        relative = source.relative_to(root).as_posix()
        if _matches(relative, patterns):
            if source.is_file() or source.is_symlink():
                excluded += 1
            continue
        if source.is_symlink():
            rejected_symlinks += 1
            continue
        if not source.is_file():
            continue
        raw = source.read_bytes()
        if b"\x00" in raw:
            excluded += 1
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            excluded += 1
            continue
        if find_secret_shapes(text):
            rejected_secrets += 1
            continue
        output = target / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        shutil.copymode(source, output)
        copied += 1

    return ProjectionManifest(
        schema="trufagent.context-projection.v1",
        copied_files=copied,
        excluded_files=excluded,
        rejected_secret_files=rejected_secrets,
        rejected_symlinks=rejected_symlinks,
    )
