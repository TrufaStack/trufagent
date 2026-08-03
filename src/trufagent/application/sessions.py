from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from trufagent.domain.memory import (
    Applicability,
    MemoryDocument,
    MemoryEnvelope,
    MemoryKind,
    MemoryRelations,
    MemoryScope,
    MemoryStatus,
    Severity,
    TrustLevel,
    Validity,
)
from trufagent.domain.session import SessionHandoff, SessionState
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_markdown import SecretShapeError, find_secret_shapes
from trufagent.infrastructure.session_fs import FileSessionRepository

Clock = Callable[[], datetime]


def _now() -> datetime:
    return datetime.now(UTC)


class StartSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1)
    objective: str | None = None


class StartSessionResult(BaseModel):
    state: SessionState
    previous_handoff: SessionHandoff | None = None
    resumed: bool
    summary: str


class MemoryProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: MemoryKind
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1)
    scope: MemoryScope = MemoryScope.PROJECT
    severity: Severity | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("scope")
    @classmethod
    def durable_session_scope(cls, scope: MemoryScope) -> MemoryScope:
        if scope == MemoryScope.USER:
            raise ValueError("session close cannot implicitly propose user memory")
        return scope


class EndSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    summary: str = Field(min_length=1)
    completed: list[str] = Field(default_factory=list)
    in_progress: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    lessons: list[str] = Field(default_factory=list)
    memory_proposals: list[MemoryProposal] = Field(default_factory=list)


class EndSessionResult(BaseModel):
    handoff: SessionHandoff
    journal_path: str
    proposed_memory_ids: list[str] = Field(default_factory=list)


class StartSessionService:
    def __init__(self, sessions: FileSessionRepository, *, clock: Clock = _now) -> None:
        self.sessions = sessions
        self.clock = clock

    def start(self, request: StartSessionRequest) -> StartSessionResult:
        current = self.sessions.current()
        previous = self.sessions.handoff()
        if current is not None:
            if current.project != request.project:
                raise ValueError(
                    f"active session belongs to {current.project!r}, not {request.project!r}"
                )
            return StartSessionResult(
                state=current,
                previous_handoff=previous,
                resumed=True,
                summary=f"Resuming {current.id}: {current.objective or 'no objective recorded'}",
            )
        now = self.clock()
        session_id = f"ses_{now.strftime('%Y%m%dT%H%M%SZ')}_{secrets.token_hex(3)}"
        state = SessionState(
            schema="trufagent.session.v1",
            id=session_id,
            project=request.project,
            started_at=now,
            updated_at=now,
            objective=request.objective,
        )
        self.sessions.save_current(state)
        next_step = previous.next_steps[0] if previous and previous.next_steps else None
        summary = f"Started {session_id}."
        if next_step:
            summary += f" Previous next step: {next_step}"
        return StartSessionResult(
            state=state,
            previous_handoff=previous,
            resumed=False,
            summary=summary,
        )


def _proposal_document(
    proposal: MemoryProposal,
    *,
    project: str,
    session_id: str,
    index: int,
    now: datetime,
) -> MemoryDocument:
    digest = hashlib.sha256(f"{session_id}:{index}:{proposal.title}".encode()).hexdigest()[:20]
    envelope = MemoryEnvelope(
        schema="trufagent.memory.v1",
        id=f"mem_{digest}",
        kind=proposal.kind,
        title=proposal.title,
        scope=proposal.scope,
        status=MemoryStatus.PROPOSED,
        trust=TrustLevel.UNREVIEWED,
        severity=proposal.severity,
        created_at=now,
        updated_at=now,
        created_by="trufagent-session",
        reviewed_by=None,
        project=project,
        tags=proposal.tags,
        applies_when=Applicability(),
        evidence=[],
        relations=MemoryRelations(),
        validity=Validity(),
    )
    return MemoryDocument(envelope=envelope, body=proposal.body)


def _journal(state: SessionState, request: EndSessionRequest, closed_at: datetime) -> str:
    sections = [
        f"# Session {state.id}",
        "",
        f"Closed: {closed_at.isoformat()}",
        "",
        "## Summary",
        "",
        request.summary,
    ]
    values = (
        ("Completed", request.completed),
        ("In progress", request.in_progress),
        ("Decisions", request.decisions),
        ("Lessons", request.lessons),
        ("Next steps", request.next_steps),
    )
    for title, items in values:
        if items:
            sections.extend(["", f"## {title}", "", *[f"- {item}" for item in items]])
    return "\n".join(sections) + "\n"


class EndSessionService:
    def __init__(
        self,
        sessions: FileSessionRepository,
        memory: MarkdownMemoryRepository,
        *,
        clock: Clock = _now,
    ) -> None:
        self.sessions = sessions
        self.memory = memory
        self.clock = clock

    def end(self, request: EndSessionRequest) -> EndSessionResult:
        current = self.sessions.current()
        if current is None:
            raise ValueError("no active session")
        if current.id != request.session_id:
            raise ValueError(f"active session {current.id!r} does not match {request.session_id!r}")
        now = self.clock()
        documents = [
            _proposal_document(
                proposal,
                project=current.project,
                session_id=current.id,
                index=index,
                now=now,
            )
            for index, proposal in enumerate(request.memory_proposals)
        ]
        for document in documents:
            shapes = find_secret_shapes(f"{document.envelope.title}\n{document.body}")
            if shapes:
                raise SecretShapeError(shapes)
        proposed_ids = [document.envelope.id for document in documents]
        handoff = SessionHandoff(
            schema="trufagent.handoff.v1",
            from_session=current.id,
            project=current.project,
            closed_at=now,
            summary=request.summary,
            completed=request.completed,
            next_steps=request.next_steps,
            decisions=request.decisions,
            proposed_memory_ids=proposed_ids,
        )
        for document in documents:
            self.memory.propose(document)
        journal_path = self.sessions.close(current, handoff, _journal(current, request, now))
        return EndSessionResult(
            handoff=handoff,
            journal_path=str(journal_path),
            proposed_memory_ids=proposed_ids,
        )
