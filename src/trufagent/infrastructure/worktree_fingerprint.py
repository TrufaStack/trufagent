from __future__ import annotations

import hashlib
import os
from pathlib import Path

_EPHEMERAL_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "graphify-out",
    "node_modules",
}
_EPHEMERAL_PREFIXES = {
    (".trufagent", "cartography"),
    (".trufagent", "state"),
}


def _is_ephemeral(relative: Path) -> bool:
    parts = relative.parts
    return any(part in _EPHEMERAL_DIRECTORIES for part in parts) or any(
        parts[: len(prefix)] == prefix for prefix in _EPHEMERAL_PREFIXES
    )


def fingerprint_worktree(project_root: Path) -> str:
    """Hash source-visible content, including ignored and untracked sensitive files."""

    root = Path(project_root).resolve()
    digest = hashlib.sha256()
    for directory, names, files in os.walk(root, topdown=True):
        current = Path(directory)
        relative_directory = current.relative_to(root)
        visible_names = sorted(
            name for name in names if not _is_ephemeral(relative_directory / name)
        )
        names[:] = []
        for name in visible_names:
            path = current / name
            relative = path.relative_to(root)
            if path.is_symlink():
                digest.update(relative.as_posix().encode())
                digest.update(b"\0symlink\0")
                digest.update(os.readlink(path).encode())
                digest.update(b"\0")
            else:
                names.append(name)
        for name in sorted(files):
            path = current / name
            relative = path.relative_to(root)
            if _is_ephemeral(relative):
                continue
            digest.update(relative.as_posix().encode())
            digest.update(b"\0")
            if path.is_symlink():
                digest.update(b"symlink\0")
                digest.update(os.readlink(path).encode())
            else:
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
            digest.update(b"\0")
    return digest.hexdigest()
