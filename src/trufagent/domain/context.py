from __future__ import annotations

from pydantic import BaseModel, Field

from trufagent.domain.cartography import GraphQueryResult
from trufagent.domain.memory import MemoryKind


class ContextItem(BaseModel):
    memory_id: str
    kind: MemoryKind
    title: str
    body: str
    governs_behavior: bool
    warnings: list[str] = Field(default_factory=list)
    estimated_tokens: int


class ContextPacket(BaseModel):
    query: str
    project: str
    items: list[ContextItem] = Field(default_factory=list)
    estimated_tokens: int = 0
    omitted_count: int = 0
    cartography: GraphQueryResult | None = None
    warnings: list[str] = Field(default_factory=list)
