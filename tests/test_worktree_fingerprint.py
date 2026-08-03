from pathlib import Path

from trufagent.infrastructure.worktree_fingerprint import fingerprint_worktree


def test_fingerprint_detects_untracked_and_sensitive_file_changes(
    tmp_path: Path,
) -> None:
    source = tmp_path / "new-source.py"
    source.write_text("before")
    secret = tmp_path / ".env"
    secret.write_text("SECRET=before")
    before = fingerprint_worktree(tmp_path)

    source.write_text("after")
    assert fingerprint_worktree(tmp_path) != before
    source.write_text("before")
    assert fingerprint_worktree(tmp_path) == before

    secret.write_text("SECRET=after")
    assert fingerprint_worktree(tmp_path) != before


def test_fingerprint_ignores_explicit_ephemeral_state(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("stable")
    before = fingerprint_worktree(tmp_path)

    state = tmp_path / ".trufagent" / "state" / "usage"
    state.mkdir(parents=True)
    (state / "session.jsonl").write_text("{}")

    assert fingerprint_worktree(tmp_path) == before


def test_fingerprint_ignores_next_build_cache_but_not_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "app" / "page.tsx"
    source.parent.mkdir()
    source.write_text("export default function Page() { return null; }")
    before = fingerprint_worktree(tmp_path)

    cache = tmp_path / ".next" / "server"
    cache.mkdir(parents=True)
    (cache / "app-page.js").write_text("generated")
    assert fingerprint_worktree(tmp_path) == before

    source.write_text("export default function Page() { return <main />; }")
    assert fingerprint_worktree(tmp_path) != before
