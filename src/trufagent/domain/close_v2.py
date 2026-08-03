from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from trufagent.domain.memory import MemoryKind


class CloseStatus(StrEnum):
    CLOSED = "closed"


class CloseMemoryProposal(BaseModel):
    """Compact v2 proposal persisted through the compatible v1 memory store."""

    model_config = ConfigDict(extra="forbid")

    kind: MemoryKind
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class CloseV2Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merged_commit: str = Field(min_length=7, max_length=64)
    base_ref: str = Field(default="HEAD", min_length=1, max_length=200)
    summary: str = Field(min_length=1)
    verifications: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    memory_proposals: list[CloseMemoryProposal] = Field(default_factory=list)


class CloseV2Result(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default="trufagent.close.v2", alias="schema")
    status: CloseStatus = CloseStatus.CLOSED
    merged_commit: str
    summary: str
    verifications: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    proposed_memory_ids: list[str] = Field(default_factory=list)
    indexed_memories: int
    graph_update_required: bool
