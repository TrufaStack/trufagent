from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from trufagent.domain.memory import (
    MemoryDocument,
    MemoryReviewEvent,
    MemoryReviewMetadata,
    MemoryStatus,
)
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_index import SqliteMemoryIndex

Clock = Callable[[], datetime]


def _now() -> datetime:
    return datetime.now(UTC)


class MemoryReviewService:
    def __init__(
        self,
        repository: MarkdownMemoryRepository,
        *,
        index: SqliteMemoryIndex | None = None,
        clock: Clock = _now,
    ) -> None:
        self.repository = repository
        self.index = index
        self.clock = clock

    def _transition(
        self,
        memory_id: str,
        *,
        expected: MemoryStatus,
        target: MemoryStatus,
        reviewer: str,
        reason: str | None = None,
        replacement_id: str | None = None,
        metadata: MemoryReviewMetadata | None = None,
    ) -> MemoryDocument:
        if not reviewer.strip():
            raise ValueError("reviewer is required")
        current = self.repository.read(memory_id)
        if current.envelope.status != expected:
            raise ValueError(
                f"memory must be {expected.value}, found {current.envelope.status.value}"
            )
        created_at = self.clock()
        payload = (
            f"{memory_id}:{expected.value}:{target.value}:{reviewer}:"
            f"{reason or ''}:{replacement_id or ''}:"
            f"{metadata.model_dump_json() if metadata else ''}:{created_at.isoformat()}"
        )
        event = MemoryReviewEvent(
            schema="trufagent.memory-review.v1",
            event_id=self.repository.review_event_id(payload),
            memory_id=memory_id,
            from_status=expected,
            to_status=target,
            reviewer=reviewer,
            reason=reason,
            replacement_id=replacement_id,
            metadata=metadata,
            created_at=created_at,
        )
        self.repository.append_review(event)
        if self.index is not None:
            self.index.rebuild(self.repository.documents())
        return self.repository.read(memory_id)

    def accept(
        self,
        memory_id: str,
        *,
        reviewer: str,
        metadata: MemoryReviewMetadata | None = None,
    ) -> MemoryDocument:
        return self._transition(
            memory_id,
            expected=MemoryStatus.PROPOSED,
            target=MemoryStatus.ACCEPTED,
            reviewer=reviewer,
            metadata=metadata,
        )

    def reject(self, memory_id: str, *, reviewer: str, reason: str) -> MemoryDocument:
        if not reason.strip():
            raise ValueError("reason is required to reject memory")
        return self._transition(
            memory_id,
            expected=MemoryStatus.PROPOSED,
            target=MemoryStatus.REJECTED,
            reviewer=reviewer,
            reason=reason,
        )

    def supersede(
        self,
        memory_id: str,
        *,
        replacement_id: str,
        reviewer: str,
        reason: str,
    ) -> MemoryDocument:
        if not reason.strip():
            raise ValueError("reason is required to supersede memory")
        replacement = self.repository.read(replacement_id)
        if replacement.envelope.status != MemoryStatus.ACCEPTED:
            raise ValueError("replacement memory must be accepted")
        return self._transition(
            memory_id,
            expected=MemoryStatus.ACCEPTED,
            target=MemoryStatus.SUPERSEDED,
            reviewer=reviewer,
            reason=reason,
            replacement_id=replacement_id,
        )

    def history(self, memory_id: str) -> list[MemoryReviewEvent]:
        document = self.repository.read(memory_id)
        return self.repository.history_for(document)
