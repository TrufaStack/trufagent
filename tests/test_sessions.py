from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trufagent.application.sessions import (
    EndSessionRequest,
    EndSessionService,
    MemoryProposal,
    StartSessionRequest,
    StartSessionService,
)
from trufagent.cli import main
from trufagent.domain.memory import MemoryKind, MemoryScope
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_markdown import SecretShapeError
from trufagent.infrastructure.session_fs import FileSessionRepository

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
LATER = datetime(2026, 7, 30, 13, 0, tzinfo=UTC)


def setup(tmp_path: Path):
    memory = MarkdownMemoryRepository(tmp_path, project="demo").initialize()
    sessions = FileSessionRepository(tmp_path)
    return memory, sessions


def test_start_is_idempotent_while_session_is_active(tmp_path: Path) -> None:
    _, sessions = setup(tmp_path)
    service = StartSessionService(sessions, clock=lambda: NOW)
    request = StartSessionRequest(project="demo", objective="Implement session lifecycle")

    first = service.start(request)
    second = service.start(request)

    assert first.state.id == second.state.id
    assert first.resumed is False
    assert second.resumed is True
    assert (tmp_path / ".trufagent/state/current-session.yaml").is_file()


def test_end_writes_journal_and_compact_handoff_without_git_commit(tmp_path: Path) -> None:
    memory, sessions = setup(tmp_path)
    started = StartSessionService(sessions, clock=lambda: NOW).start(
        StartSessionRequest(project="demo", objective="Build sessions")
    )

    result = EndSessionService(sessions, memory, clock=lambda: LATER).end(
        EndSessionRequest(
            session_id=started.state.id,
            summary="Implemented the session lifecycle.",
            completed=["Session models", "Filesystem repository"],
            next_steps=["Expose CLI"],
            decisions=["Session close never commits Git"],
        )
    )

    assert result.handoff.next_steps == ["Expose CLI"]
    assert Path(result.journal_path).is_file()
    assert not (tmp_path / ".trufagent/state/current-session.yaml").exists()
    assert not (tmp_path / ".git").exists()
    journal = Path(result.journal_path).read_text()
    assert "Filesystem repository" in journal
    assert "Session close never commits Git" in journal


def test_next_start_reads_only_compact_handoff(tmp_path: Path) -> None:
    memory, sessions = setup(tmp_path)
    first = StartSessionService(sessions, clock=lambda: NOW).start(
        StartSessionRequest(project="demo", objective="First objective")
    )
    EndSessionService(sessions, memory, clock=lambda: LATER).end(
        EndSessionRequest(
            session_id=first.state.id,
            summary="Finished phase one.",
            next_steps=["Start phase two"],
        )
    )

    resumed = StartSessionService(sessions, clock=lambda: datetime(2026, 7, 31, tzinfo=UTC)).start(
        StartSessionRequest(project="demo", objective="Phase two")
    )

    assert resumed.previous_handoff is not None
    assert resumed.previous_handoff.summary == "Finished phase one."
    assert "Start phase two" in resumed.summary


def test_end_creates_only_unreviewed_non_governing_memory_proposals(tmp_path: Path) -> None:
    memory, sessions = setup(tmp_path)
    started = StartSessionService(sessions, clock=lambda: NOW).start(
        StartSessionRequest(project="demo")
    )

    result = EndSessionService(sessions, memory, clock=lambda: LATER).end(
        EndSessionRequest(
            session_id=started.state.id,
            summary="Found a durable distinction.",
            memory_proposals=[
                MemoryProposal(
                    kind=MemoryKind.DECISION,
                    title="Keep session state outside Git",
                    body="Session journals are ephemeral; accepted decisions require review.",
                    scope=MemoryScope.PROJECT,
                )
            ],
        )
    )

    proposed = memory.read(result.proposed_memory_ids[0])
    assert proposed.envelope.status.value == "proposed"
    assert proposed.envelope.trust.value == "unreviewed"
    assert proposed.envelope.governs_behavior is False


def test_secret_in_proposal_blocks_close_and_keeps_session_active(tmp_path: Path) -> None:
    memory, sessions = setup(tmp_path)
    started = StartSessionService(sessions, clock=lambda: NOW).start(
        StartSessionRequest(project="demo")
    )

    with pytest.raises(SecretShapeError):
        EndSessionService(sessions, memory, clock=lambda: LATER).end(
            EndSessionRequest(
                session_id=started.state.id,
                summary="Unsafe proposal",
                memory_proposals=[
                    MemoryProposal(
                        kind=MemoryKind.LESSON,
                        title="Database access",
                        body="db_password=super-secret-password",
                    )
                ],
            )
        )

    assert sessions.current().id == started.state.id


def test_end_rejects_wrong_session_id(tmp_path: Path) -> None:
    memory, sessions = setup(tmp_path)
    StartSessionService(sessions, clock=lambda: NOW).start(StartSessionRequest(project="demo"))

    with pytest.raises(ValueError, match="does not match"):
        EndSessionService(sessions, memory, clock=lambda: LATER).end(
            EndSessionRequest(session_id="ses_wrong", summary="No")
        )


def test_session_cannot_implicitly_propose_user_memory() -> None:
    with pytest.raises(ValueError, match="user memory"):
        MemoryProposal(
            kind=MemoryKind.PREFERENCE,
            title="Personal preference",
            body="Always use a particular tool.",
            scope=MemoryScope.USER,
        )


def test_cli_start_status_end_lifecycle(tmp_path: Path, capsys) -> None:
    MarkdownMemoryRepository(tmp_path, project="demo").initialize()

    assert (
        main(
            [
                "session",
                "start",
                str(tmp_path),
                "--project",
                "demo",
                "--objective",
                "Test CLI",
            ]
        )
        == 0
    )
    session_id = json.loads(capsys.readouterr().out)["state"]["id"]

    assert main(["session", "status", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == session_id

    request = tmp_path / "end.json"
    request.write_text(
        EndSessionRequest(
            session_id=session_id,
            summary="CLI lifecycle works.",
            next_steps=["Continue"],
        ).model_dump_json()
    )
    assert main(["session", "end", str(tmp_path), str(request), "--project", "demo"]) == 0
    assert json.loads(capsys.readouterr().out)["handoff"]["summary"] == ("CLI lifecycle works.")


def test_cli_session_commands_infer_project_from_config(tmp_path: Path, capsys) -> None:
    initialize = tmp_path / ".trufagent"
    initialize.mkdir()
    (initialize / "config.yaml").write_text(
        "schema: trufagent.project.v1\nproject: demo\nskills:\n  catalog: /tmp/catalog.yaml\n"
    )

    assert main(["session", "start", str(tmp_path), "--objective", "Adapter"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["state"]["project"] == "demo"
