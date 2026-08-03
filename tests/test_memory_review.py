from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from trufagent.application.memory_review import MemoryReviewService
from trufagent.cli import main
from trufagent.domain.memory import (
    Applicability,
    EvidenceReference,
    MemoryReviewMetadata,
    MemoryStatus,
)
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_index import SqliteMemoryIndex
from trufagent.infrastructure.memory_markdown import load_memory_markdown, parse_memory_markdown

FIXTURES = Path(__file__).parent / "fixtures" / "memory"
NOW = datetime(2026, 7, 30, 14, 0, tzinfo=UTC)


def proposed_risk():
    text = (FIXTURES / "c02-checklist-risk.md").read_text()
    text = text.replace("status: accepted", "status: proposed")
    text = text.replace("trust: code-verified", "trust: unreviewed")
    text = text.replace("reviewed_by: user", "reviewed_by:")
    return parse_memory_markdown(text)


def setup(tmp_path: Path):
    repository = MarkdownMemoryRepository(tmp_path, project="jc-app").initialize()
    document = proposed_risk()
    path = repository.propose(document)
    service = MemoryReviewService(repository, clock=lambda: NOW)
    return repository, service, document, path


def test_accept_makes_governing_without_rewriting_original_markdown(tmp_path: Path) -> None:
    repository, service, document, original_path = setup(tmp_path)
    original = original_path.read_text()

    reviewed = service.accept(document.envelope.id, reviewer="user")

    assert reviewed.envelope.status == MemoryStatus.ACCEPTED
    assert reviewed.envelope.governs_behavior is True
    assert reviewed.envelope.reviewed_by == "user"
    assert original_path.read_text() == original
    events = list((original_path.parent / ".events" / document.envelope.id).glob("*.yaml"))
    assert len(events) == 1


def test_accept_event_enriches_effective_memory_without_rewriting_source(
    tmp_path: Path,
) -> None:
    repository, service, document, original_path = setup(tmp_path)
    original = original_path.read_text()

    reviewed = service.accept(
        document.envelope.id,
        reviewer="user",
        metadata=MemoryReviewMetadata(
            applies_when=Applicability(
                concepts=["checklist-routing"],
                symbols=["resolveChecklistJobType"],
            ),
            evidence=[
                EvidenceReference(
                    type="test",
                    ref="tests/test_record_route_job_type.py",
                )
            ],
        ),
    )

    assert reviewed.envelope.applies_when.symbols == ["resolveChecklistJobType"]
    assert reviewed.envelope.evidence[0].ref == ("tests/test_record_route_job_type.py")
    assert original_path.read_text() == original
    history = service.history(document.envelope.id)
    assert history[0].metadata is not None


def test_reject_requires_reason_and_disappears_from_normal_recall(tmp_path: Path) -> None:
    repository, service, document, _ = setup(tmp_path)

    with pytest.raises(ValueError, match="reason"):
        service.reject(document.envelope.id, reviewer="user", reason="")
    service.reject(document.envelope.id, reviewer="user", reason="Incorrect assumption")

    assert repository.read(document.envelope.id).envelope.status == MemoryStatus.REJECTED
    assert repository.search("checklist persistence") == []


def test_supersede_requires_accepted_replacement_and_links_it(tmp_path: Path) -> None:
    repository, service, old, _ = setup(tmp_path)
    service.accept(old.envelope.id, reviewer="user")
    replacement_text = (FIXTURES / "c09-greendeal-negative-decision.md").read_text()
    replacement = load_memory_markdown(FIXTURES / "c09-greendeal-negative-decision.md")
    repository.propose(replacement)

    reviewed = service.supersede(
        old.envelope.id,
        replacement_id=replacement.envelope.id,
        reviewer="user",
        reason="A newer verified decision replaces it",
    )

    assert reviewed.envelope.status == MemoryStatus.SUPERSEDED
    assert reviewed.envelope.relations.superseded_by == [replacement.envelope.id]
    assert repository.search("checklist persistence") == []
    assert replacement_text


def test_invalid_transition_is_rejected(tmp_path: Path) -> None:
    _, service, document, _ = setup(tmp_path)
    service.accept(document.envelope.id, reviewer="user")

    with pytest.raises(ValueError, match="accepted"):
        service.accept(document.envelope.id, reviewer="user")
    with pytest.raises(ValueError, match="proposed"):
        service.reject(document.envelope.id, reviewer="user", reason="Too late")


def test_review_rebuilds_derived_index_when_configured(tmp_path: Path) -> None:
    repository, _, document, _ = setup(tmp_path)
    index = SqliteMemoryIndex(tmp_path / ".trufagent" / "memory-index.sqlite3")
    service = MemoryReviewService(repository, index=index, clock=lambda: NOW)

    service.accept(document.envelope.id, reviewer="user")

    assert index.search("checklist routing", project="jc-app")[0].memory_id == (
        document.envelope.id
    )


def test_review_history_is_available_for_audit(tmp_path: Path) -> None:
    _, service, document, _ = setup(tmp_path)
    service.accept(document.envelope.id, reviewer="alice")

    history = service.history(document.envelope.id)

    assert history[0].from_status == MemoryStatus.PROPOSED
    assert history[0].to_status == MemoryStatus.ACCEPTED
    assert history[0].reviewer == "alice"


def test_invalid_effective_transition_is_rejected_before_event_write(
    tmp_path: Path,
) -> None:
    repository, _, document, original_path = setup(tmp_path)
    service = MemoryReviewService(
        repository,
        clock=lambda: datetime(2020, 1, 1, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="updated_at"):
        service.accept(document.envelope.id, reviewer="user")

    events_root = original_path.parent / ".events" / document.envelope.id
    assert not events_root.exists()
    assert repository.read(document.envelope.id).envelope.status == MemoryStatus.PROPOSED


def test_cli_lists_shows_accepts_and_reports_history(tmp_path: Path, capsys) -> None:
    repository, _, document, _ = setup(tmp_path)

    assert main(["memory", "list", str(tmp_path), "--project", "jc-app"]) == 0
    assert document.envelope.id in capsys.readouterr().out
    assert (
        main(
            [
                "memory",
                "accept",
                str(tmp_path),
                document.envelope.id,
                "--project",
                "jc-app",
                "--reviewer",
                "user",
            ]
        )
        == 0
    )
    assert '"status":"accepted"' in capsys.readouterr().out
    assert (
        main(
            [
                "memory",
                "history",
                str(tmp_path),
                document.envelope.id,
                "--project",
                "jc-app",
            ]
        )
        == 0
    )
    assert "memory-review.v1" in capsys.readouterr().out
    assert repository.read(document.envelope.id).envelope.governs_behavior
