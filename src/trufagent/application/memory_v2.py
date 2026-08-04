from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from trufagent.domain.memory import MemoryKind
from trufagent.domain.memory_v2 import (
    MemoryActionV2,
    MemoryDocumentV2,
    MemoryEnvelopeV2,
    MemoryEventV2,
    MemoryStateV2,
)
from trufagent.infrastructure.memory_index import SqliteMemoryIndex
from trufagent.infrastructure.memory_v2_fs import MarkdownMemoryRepositoryV2

Clock = Callable[[], datetime]


def _now() -> datetime:
    return datetime.now(UTC)


class MemoryV2Service:
    def __init__(
        self,
        repository: MarkdownMemoryRepositoryV2,
        *,
        index: SqliteMemoryIndex | None = None,
        legacy_documents: Callable[[], Iterable] = tuple,
        clock: Clock = _now,
    ) -> None:
        self.repository = repository
        self.index = index
        self.legacy_documents = legacy_documents
        self.clock = clock

    def _rebuild(self) -> None:
        if self.index is not None:
            self.index.rebuild([*self.legacy_documents(), *self.repository.documents()])

    def propose(
        self,
        *,
        kind: MemoryKind,
        title: str,
        body: str,
        source_commit: str | None = None,
        tags: list[str] | None = None,
    ) -> MemoryDocumentV2:
        now = self.clock()
        digest = hashlib.sha256(f"{self.repository.project}:{title}:{body}".encode()).hexdigest()[
            :20
        ]
        document = MemoryDocumentV2(
            envelope=MemoryEnvelopeV2(
                schema="trufagent.memory.v2",
                id=f"mem_{digest}",
                kind=kind,
                title=title,
                status=MemoryStateV2.PROPOSED,
                project=self.repository.project,
                created_at=now,
                updated_at=now,
                source_commit=source_commit,
                tags=tags or [],
            ),
            body=body,
        )
        self.repository.propose(document)
        self._rebuild()
        return self.repository.read(document.envelope.id)

    def _event(
        self,
        memory_id: str,
        action: MemoryActionV2,
        *,
        reviewer: str,
        replacement_id: str | None = None,
        reason: str | None = None,
    ) -> MemoryDocumentV2:
        now = self.clock()
        payload = f"{memory_id}:{action}:{reviewer}:{replacement_id}:{reason}:{now.isoformat()}"
        self.repository.append(
            MemoryEventV2(
                schema="trufagent.memory-event.v2",
                event_id=self.repository.event_id(payload),
                memory_id=memory_id,
                action=action,
                reviewer=reviewer,
                replacement_id=replacement_id,
                reason=reason,
                created_at=now,
            )
        )
        self._rebuild()
        return self.repository.read(memory_id)

    def accept(self, memory_id: str, *, reviewer: str) -> MemoryDocumentV2:
        return self._event(memory_id, MemoryActionV2.ACCEPT, reviewer=reviewer)

    def replace(
        self, memory_id: str, *, replacement_id: str, reviewer: str, reason: str
    ) -> MemoryDocumentV2:
        return self._event(
            memory_id,
            MemoryActionV2.REPLACE,
            reviewer=reviewer,
            replacement_id=replacement_id,
            reason=reason,
        )

    def retire(self, memory_id: str, *, reviewer: str, reason: str) -> MemoryDocumentV2:
        return self._event(memory_id, MemoryActionV2.RETIRE, reviewer=reviewer, reason=reason)
