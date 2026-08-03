from __future__ import annotations

import subprocess
from pathlib import Path


class GitMergeVerifier:
    """Confirm that a commit is reachable from the requested base ref."""

    def contains(self, project_root: Path, commit: str, base_ref: str) -> bool:
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, base_ref],
            cwd=Path(project_root).resolve(),
            capture_output=True,
            check=False,
            text=True,
        )
        if completed.returncode == 0:
            return True
        if completed.returncode == 1:
            return False
        detail = completed.stderr.strip() or "git could not verify merged commit"
        raise ValueError(detail)
