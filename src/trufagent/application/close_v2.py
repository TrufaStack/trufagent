from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from trufagent.domain.cartography import GraphState, GraphStatus
from trufagent.domain.close_v2 import CloseV2Request, CloseV2Result
from trufagent.domain.memory import (
    Applicability,
    MemoryDocument,
    MemoryEnvelope,
    MemoryRelations,
    MemoryScope,
    MemoryStatus,
    TrustLevel,
    Validity,
)
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_index import SqliteMemoryIndex

Clock = Callable[[], datetime]


def _now() -> datetime:
    return datetime.now(UTC)


class MergeVerifier(Protocol):
    def contains(self, project_root: Path, commit: str, base_ref: str) -> bool: ...


class CartographyStatus(Protocol):
    def status(self, project_root: Path) -> GraphStatus: ...


class CloseV2Service:
    def __init__(
        self,
        memory: MarkdownMemoryRepository,
        index: SqliteMemoryIndex,
        merge: MergeVerifier,
        cartography: CartographyStatus,
        *,
        project: str,
        clock: Clock = _now,
    ) -> None:
        self.memory = memory
        self.index = index
        self.merge = merge
        self.cartography = cartography
        self.project = project
        self.clock = clock

    def close(self, project_root: Path, request: CloseV2Request) -> CloseV2Result:
        if not self.merge.contains(project_root, request.merged_commit, request.base_ref):
            raise ValueError(
                f"commit {request.merged_commit!r} is not merged into {request.base_ref!r}"
            )

        graph = self.cartography.status(project_root)
        now = self.clock()
        proposed_ids: list[str] = []
        for position, proposal in enumerate(request.memory_proposals):
            digest = hashlib.sha256(
                f"{request.merged_commit}:{position}:{proposal.title}".encode()
            ).hexdigest()[:20]
            document = MemoryDocument(
                envelope=MemoryEnvelope(
                    schema="trufagent.memory.v1",
                    id=f"mem_{digest}",
                    kind=proposal.kind,
                    title=proposal.title,
                    scope=MemoryScope.PROJECT,
                    status=MemoryStatus.PROPOSED,
                    trust=TrustLevel.UNREVIEWED,
                    created_at=now,
                    updated_at=now,
                    created_by="trufagent-close-v2",
                    project=self.project,
                    tags=proposal.tags,
                    applies_when=Applicability(),
                    relations=MemoryRelations(),
                    validity=Validity(derived_from_commit=request.merged_commit),
                ),
                body=proposal.body,
            )
            self.memory.propose(document)
            proposed_ids.append(document.envelope.id)

        indexed = self.index.rebuild(self.memory.documents())
        return CloseV2Result(
            merged_commit=request.merged_commit,
            summary=request.summary,
            verifications=request.verifications,
            decisions=request.decisions,
            proposed_memory_ids=proposed_ids,
            indexed_memories=indexed,
            graph_update_required=graph.state != GraphState.FRESH,
        )
