from __future__ import annotations

from pathlib import Path
from typing import Protocol

from trufagent.domain.cartography import GraphQueryResult, GraphStatus
from trufagent.domain.memory import MemoryDocument


class MemoryRepository(Protocol):
    def read(self, memory_id: str) -> MemoryDocument: ...

    def search(
        self,
        query: str,
        *,
        project: str | None = None,
        limit: int = 10,
        include_user: bool = False,
    ) -> list[MemoryDocument]: ...

    def propose(self, document: MemoryDocument) -> Path: ...


class CartographyPort(Protocol):
    def status(self, project_root: Path) -> GraphStatus: ...

    def update(self, project_root: Path) -> GraphStatus: ...

    def query(
        self, project_root: Path, question: str, *, token_budget: int = 2_000
    ) -> GraphQueryResult: ...

    def affected(
        self, project_root: Path, label: str, *, relations: list[str], depth: int = 2
    ) -> GraphQueryResult: ...
