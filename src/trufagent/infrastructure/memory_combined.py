from __future__ import annotations

from trufagent.domain.memory import MemoryDocument
from trufagent.domain.memory_v2 import MemoryDocumentV2
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository, MemoryVaultError
from trufagent.infrastructure.memory_v2_fs import MarkdownMemoryRepositoryV2


class CombinedMemoryRepository:
    """Read v1 and native v2 memory through one stable retrieval boundary."""

    def __init__(
        self,
        legacy: MarkdownMemoryRepository,
        native: MarkdownMemoryRepositoryV2,
    ) -> None:
        self.legacy = legacy
        self.native = native

    def search(
        self,
        query: str,
        *,
        project: str | None = None,
        limit: int = 10,
        include_user: bool = False,
    ) -> list[MemoryDocument | MemoryDocumentV2]:
        documents: list[MemoryDocument | MemoryDocumentV2] = [
            *self.legacy.search(
                query,
                project=project,
                limit=limit,
                include_user=include_user,
            ),
            *self.native.search(query, project=project, limit=limit),
        ]
        ids = [document.envelope.id for document in documents]
        duplicates = sorted({memory_id for memory_id in ids if ids.count(memory_id) > 1})
        if duplicates:
            joined = ", ".join(duplicates)
            raise MemoryVaultError(f"memory ids collide across v1 and v2: {joined}")
        return documents
