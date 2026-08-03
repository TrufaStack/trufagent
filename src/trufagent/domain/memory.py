from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MemoryKind(StrEnum):
    RULE = "rule"
    ENVIRONMENT_FACT = "environment_fact"
    DECISION = "decision"
    NEGATIVE_DECISION = "negative_decision"
    RISK = "risk"
    INCIDENT = "incident"
    LESSON = "lesson"
    EXTERNAL_ARTIFACT = "external_artifact"
    STRUCTURAL_FACT = "structural_fact"
    PREFERENCE = "preference"
    CONTEXT = "context"
    HANDOFF = "handoff"


class MemoryScope(StrEnum):
    PROJECT = "project"
    TEAM = "team"
    USER = "user"


class MemoryStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    STALE = "stale"
    RESOLVED = "resolved"


class TrustLevel(StrEnum):
    UNREVIEWED = "unreviewed"
    HUMAN_REVIEWED = "human-reviewed"
    CODE_VERIFIED = "code-verified"
    EXTERNALLY_VERIFIED = "externally-verified"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Applicability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concepts: list[str] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    ref: str


class MemoryRelations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    affects: list[str] = Field(default_factory=list)
    caused_by: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: list[str] = Field(default_factory=list)
    related_to: list[str] = Field(default_factory=list)


class Validity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_from: date | None = None
    review_after: date | None = None
    derived_from_commit: str | None = None


class MemoryEnvelope(BaseModel):
    """Canonical frontmatter for a Trufagent memory document."""

    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.memory\.v1$")
    id: str = Field(pattern=r"^mem_[A-Za-z0-9][A-Za-z0-9_-]{5,63}$")
    kind: MemoryKind
    title: str = Field(min_length=1, max_length=160)
    scope: MemoryScope
    status: MemoryStatus
    trust: TrustLevel
    severity: Severity | None = None
    created_at: datetime
    updated_at: datetime
    created_by: str = Field(min_length=1, max_length=80)
    reviewed_by: str | None = Field(default=None, max_length=80)
    project: str = Field(min_length=1, max_length=160)
    tags: list[str] = Field(default_factory=list)
    applies_when: Applicability = Field(default_factory=Applicability)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    relations: MemoryRelations = Field(default_factory=MemoryRelations)
    validity: Validity = Field(default_factory=Validity)

    @field_validator("tags")
    @classmethod
    def unique_tags(cls, tags: list[str]) -> list[str]:
        return list(dict.fromkeys(tags))

    @model_validator(mode="after")
    def validate_governance(self) -> MemoryEnvelope:
        governing_kinds = {
            MemoryKind.RULE,
            MemoryKind.DECISION,
            MemoryKind.NEGATIVE_DECISION,
            MemoryKind.RISK,
            MemoryKind.PREFERENCE,
        }
        if self.status == MemoryStatus.ACCEPTED and self.kind in governing_kinds:
            if self.trust == TrustLevel.UNREVIEWED or not self.reviewed_by:
                raise ValueError("accepted governing memory requires human review")
        if self.kind in {MemoryKind.RISK, MemoryKind.INCIDENT} and self.severity is None:
            raise ValueError("risk and incident memories require severity")
        if self.status == MemoryStatus.SUPERSEDED and not self.relations.superseded_by:
            raise ValueError("superseded memory requires relations.superseded_by")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self

    @property
    def governs_behavior(self) -> bool:
        governing_kinds = {
            MemoryKind.RULE,
            MemoryKind.DECISION,
            MemoryKind.NEGATIVE_DECISION,
            MemoryKind.RISK,
            MemoryKind.PREFERENCE,
        }
        return (
            self.kind in governing_kinds
            and self.status == MemoryStatus.ACCEPTED
            and self.trust != TrustLevel.UNREVIEWED
            and self.reviewed_by is not None
        )


class MemoryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    envelope: MemoryEnvelope
    body: str = Field(min_length=1)
    source_path: str | None = None


class MemoryReviewMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applies_when: Applicability | None = None
    evidence: list[EvidenceReference] | None = None
    relations: MemoryRelations | None = None
    validity: Validity | None = None

    @model_validator(mode="after")
    def has_enrichment(self) -> MemoryReviewMetadata:
        if all(
            value is None
            for value in (
                self.applies_when,
                self.evidence,
                self.relations,
                self.validity,
            )
        ):
            raise ValueError("review metadata must enrich at least one field")
        return self


class MemoryReviewEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.memory-review\.v1$")
    event_id: str = Field(pattern=r"^rev_[a-f0-9]{16,64}$")
    memory_id: str
    from_status: MemoryStatus
    to_status: MemoryStatus
    reviewer: str = Field(min_length=1)
    reason: str | None = None
    replacement_id: str | None = None
    metadata: MemoryReviewMetadata | None = None
    created_at: datetime


def memory_json_schema() -> dict[str, Any]:
    return MemoryEnvelope.model_json_schema(by_alias=True)
