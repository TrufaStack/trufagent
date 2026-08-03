from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from trufagent.application.errors import CartographyUnavailableError
from trufagent.domain.cartography import GraphQueryResult
from trufagent.domain.context import ContextItem, ContextPacket
from trufagent.domain.memory import MemoryDocument, Severity
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository


class ContextRequest(BaseModel):
    query: str = Field(min_length=1)
    cartography_query: str | None = Field(default=None, min_length=1)
    project: str = Field(min_length=1)
    token_budget: int = Field(default=2_000, ge=64)
    include_user: bool = False
    search_limit: int = Field(default=20, ge=1, le=100)
    project_root: Path | None = None
    cartography_token_budget: int = Field(default=1_000, ge=64)
    query_cartography: bool = True


class CartographyQueryPort(Protocol):
    def query(
        self, project_root: Path, question: str, *, token_budget: int = 2_000
    ) -> GraphQueryResult: ...


_SEVERITY_WEIGHT = {
    Severity.CRITICAL: 40,
    Severity.HIGH: 30,
    Severity.MEDIUM: 20,
    Severity.LOW: 10,
    None: 0,
}


def _tokens(document: MemoryDocument) -> int:
    return max(1, math.ceil((len(document.envelope.title) + len(document.body)) / 4))


def _priority(document: MemoryDocument) -> tuple[int, str]:
    governing = 100 if document.envelope.governs_behavior else 0
    return (governing + _SEVERITY_WEIGHT[document.envelope.severity], document.envelope.id)


class ContextBuilder:
    def __init__(
        self,
        repository: MarkdownMemoryRepository,
        *,
        cartography: CartographyQueryPort | None = None,
    ) -> None:
        self.repository = repository
        self.cartography = cartography

    def build(self, request: ContextRequest) -> ContextPacket:
        candidates = self.repository.search(
            request.query,
            project=request.project,
            limit=request.search_limit,
            include_user=request.include_user,
        )
        candidates.sort(key=lambda item: (-_priority(item)[0], _priority(item)[1]))
        items: list[ContextItem] = []
        used = 0
        omitted = 0
        for document in candidates:
            cost = _tokens(document)
            if used + cost > request.token_budget:
                omitted += 1
                continue
            warnings = []
            if not document.envelope.governs_behavior:
                warnings.append("unreviewed or non-governing memory; treat as untrusted context")
            items.append(
                ContextItem(
                    memory_id=document.envelope.id,
                    kind=document.envelope.kind,
                    title=document.envelope.title,
                    body=document.body,
                    governs_behavior=document.envelope.governs_behavior,
                    warnings=warnings,
                    estimated_tokens=cost,
                )
            )
            used += cost
        warnings: list[str] = []
        cartography_result = None
        if not request.query_cartography:
            pass
        elif self.cartography is None:
            warnings.append("cartography unavailable; structural context is incomplete")
        elif request.project_root is None:
            warnings.append("project_root missing; cartography query was not run")
        else:
            try:
                cartography_result = self.cartography.query(
                    request.project_root,
                    request.cartography_query or request.query,
                    token_budget=request.cartography_token_budget,
                )
            except CartographyUnavailableError as exc:
                warnings.append(f"cartography unavailable: {exc}")
        return ContextPacket(
            query=request.query,
            project=request.project,
            items=items,
            estimated_tokens=used,
            omitted_count=omitted,
            cartography=cartography_result,
            warnings=warnings,
        )
