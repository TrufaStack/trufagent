from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trufagent.domain.memory import MemoryDocument, MemoryKind, MemoryStatus


class MemoryStateV2(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REPLACED = "replaced"
    RETIRED = "retired"


class MemoryEnvelopeV2(BaseModel):
    """Compact canonical metadata for an agile v2 memory."""

    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.memory\.v2$")
    id: str = Field(pattern=r"^mem_[A-Za-z0-9][A-Za-z0-9_-]{5,63}$")
    kind: MemoryKind
    title: str = Field(min_length=1, max_length=160)
    status: MemoryStateV2
    project: str = Field(min_length=1, max_length=160)
    created_at: datetime
    updated_at: datetime
    reviewed_by: str | None = Field(default=None, max_length=80)
    source_commit: str | None = Field(default=None, min_length=7, max_length=64)
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def unique_tags(cls, tags: list[str]) -> list[str]:
        return list(dict.fromkeys(tags))

    @model_validator(mode="after")
    def validate_review(self) -> MemoryEnvelopeV2:
        if self.status == MemoryStateV2.ACCEPTED and not self.reviewed_by:
            raise ValueError("accepted v2 memory requires human review")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self

    @property
    def governs_behavior(self) -> bool:
        governing = {
            MemoryKind.RULE,
            MemoryKind.DECISION,
            MemoryKind.NEGATIVE_DECISION,
            MemoryKind.RISK,
            MemoryKind.PREFERENCE,
        }
        return (
            self.kind in governing
            and self.status == MemoryStateV2.ACCEPTED
            and self.reviewed_by is not None
        )


class MemoryDocumentV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    envelope: MemoryEnvelopeV2
    body: str = Field(min_length=1)
    source_path: str | None = None


def project_v1_memory(document: MemoryDocument) -> MemoryDocumentV2:
    states = {
        MemoryStatus.PROPOSED: MemoryStateV2.PROPOSED,
        MemoryStatus.ACCEPTED: MemoryStateV2.ACCEPTED,
        MemoryStatus.SUPERSEDED: MemoryStateV2.REPLACED,
        MemoryStatus.REJECTED: MemoryStateV2.RETIRED,
        MemoryStatus.STALE: MemoryStateV2.RETIRED,
        MemoryStatus.RESOLVED: MemoryStateV2.RETIRED,
    }
    source_commit = document.envelope.validity.derived_from_commit
    if source_commit is not None and len(source_commit) < 7:
        source_commit = None
    return MemoryDocumentV2(
        envelope=MemoryEnvelopeV2(
            schema="trufagent.memory.v2",
            id=document.envelope.id,
            kind=document.envelope.kind,
            title=document.envelope.title,
            status=states[document.envelope.status],
            project=document.envelope.project,
            created_at=document.envelope.created_at,
            updated_at=document.envelope.updated_at,
            reviewed_by=document.envelope.reviewed_by,
            source_commit=source_commit,
            tags=document.envelope.tags,
        ),
        body=document.body,
        source_path=document.source_path,
    )


def memory_v2_json_schema() -> dict[str, Any]:
    return MemoryEnvelopeV2.model_json_schema(by_alias=True)
