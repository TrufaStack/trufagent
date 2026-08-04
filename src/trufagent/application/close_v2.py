from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from trufagent.application.memory_v2 import MemoryV2Service
from trufagent.domain.cartography import GraphState, GraphStatus
from trufagent.domain.close_v2 import CloseV2Request, CloseV2Result
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_index import SqliteMemoryIndex
from trufagent.infrastructure.memory_v2_fs import MarkdownMemoryRepositoryV2

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
        memory: MarkdownMemoryRepositoryV2,
        legacy_memory: MarkdownMemoryRepository,
        index: SqliteMemoryIndex,
        merge: MergeVerifier,
        cartography: CartographyStatus,
        *,
        project: str,
        clock: Clock = _now,
    ) -> None:
        self.memory = memory
        self.legacy_memory = legacy_memory
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
        memory_service = MemoryV2Service(
            self.memory,
            index=self.index,
            legacy_documents=self.legacy_memory.documents,
            clock=self.clock,
        )
        proposed_ids: list[str] = []
        for proposal in request.memory_proposals:
            document = memory_service.propose(
                kind=proposal.kind,
                title=proposal.title,
                body=proposal.body,
                source_commit=request.merged_commit,
                tags=proposal.tags,
            )
            proposed_ids.append(document.envelope.id)

        indexed = self.index.rebuild([*self.legacy_memory.documents(), *self.memory.documents()])
        return CloseV2Result(
            merged_commit=request.merged_commit,
            summary=request.summary,
            verifications=request.verifications,
            decisions=request.decisions,
            proposed_memory_ids=proposed_ids,
            indexed_memories=indexed,
            graph_update_required=graph.state != GraphState.FRESH,
        )
