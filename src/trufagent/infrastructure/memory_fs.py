from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

from trufagent.domain.memory import (
    MemoryDocument,
    MemoryEnvelope,
    MemoryReviewEvent,
    MemoryScope,
    MemoryStatus,
    TrustLevel,
)
from trufagent.infrastructure.memory_markdown import (
    SecretShapeError,
    find_secret_shapes,
    load_memory_markdown,
)

PROTECTIVE_GITIGNORE = """# Managed by Trufagent. Changes require explicit migration.
/memory/project/
/state/
/cartography/
/memory-index.sqlite3
"""

_EXCLUDED_STATUSES = {
    MemoryStatus.REJECTED,
    MemoryStatus.SUPERSEDED,
    MemoryStatus.STALE,
}


class MemoryVaultError(RuntimeError):
    pass


class MemoryAlreadyExistsError(MemoryVaultError):
    pass


class MemoryIsolationError(MemoryVaultError):
    pass


def _render(document: MemoryDocument) -> str:
    data = document.envelope.model_dump(by_alias=True, mode="json")
    frontmatter = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{frontmatter}\n---\n{document.body.strip()}\n"


class MarkdownMemoryRepository:
    """Canonical Markdown/YAML memory with explicit scope boundaries."""

    def __init__(
        self,
        project_root: Path,
        *,
        project: str,
        user_memory_root: Path | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.project = project
        self.vault = self.project_root / ".trufagent"
        self.user_memory_root = Path(user_memory_root) if user_memory_root else None

    def initialize(self) -> MarkdownMemoryRepository:
        protection = self.vault / ".gitignore"
        if protection.exists() and protection.read_text(encoding="utf-8") != PROTECTIVE_GITIGNORE:
            raise MemoryVaultError("vault protection differs from the required fail-closed policy")
        for path in (
            self.vault / "memory" / "project",
            self.vault / "memory" / "team",
            self.vault / "state",
            self.vault / "cartography",
        ):
            path.mkdir(parents=True, exist_ok=True)
        if not protection.exists():
            protection.write_text(PROTECTIVE_GITIGNORE, encoding="utf-8")
        return self

    def _root_for(self, scope: MemoryScope) -> Path:
        if scope == MemoryScope.USER:
            if self.user_memory_root is None:
                raise MemoryIsolationError("user memory requires an explicit user_memory_root")
            return self.user_memory_root
        return self.vault / "memory" / scope.value

    def _validate_project(self, document: MemoryDocument) -> None:
        declared = document.envelope.project
        if declared not in {self.project, "*"}:
            raise MemoryIsolationError(
                f"memory belongs to project {declared!r}, current project is {self.project!r}"
            )
        if declared == "*" and document.envelope.scope != MemoryScope.USER:
            raise MemoryIsolationError("wildcard project is only valid for explicit user memory")

    def propose(self, document: MemoryDocument) -> Path:
        shapes = find_secret_shapes(f"{document.envelope.title}\n{document.body}")
        if shapes:
            raise SecretShapeError(shapes)
        self._validate_project(document)
        root = self._root_for(document.envelope.scope)
        root.mkdir(parents=True, exist_ok=True)
        destination = root / f"{document.envelope.id}.md"
        if destination.exists() or any(
            item.envelope.id == document.envelope.id for item in self.documents(include_user=True)
        ):
            raise MemoryAlreadyExistsError(f"memory {document.envelope.id!r} already exists")
        destination.write_text(_render(document), encoding="utf-8")
        return destination

    def documents(self, *, include_user: bool = False) -> list[MemoryDocument]:
        roots = [self.vault / "memory" / "project", self.vault / "memory" / "team"]
        if include_user and self.user_memory_root is not None:
            roots.append(self.user_memory_root)
        documents: list[MemoryDocument] = []
        for root in roots:
            if root.exists():
                documents.extend(load_memory_markdown(path) for path in sorted(root.glob("*.md")))
        return [
            self._effective(document) for document in documents if self._matches_project(document)
        ]

    @staticmethod
    def _events_root(document: MemoryDocument) -> Path:
        if document.source_path is None:
            raise MemoryVaultError("persisted memory has no source path")
        return Path(document.source_path).parent / ".events" / document.envelope.id

    def history_for(self, document: MemoryDocument) -> list[MemoryReviewEvent]:
        root = self._events_root(document)
        if not root.is_dir():
            return []
        events: list[MemoryReviewEvent] = []
        for path in sorted(root.glob("*.yaml")):
            try:
                events.append(
                    MemoryReviewEvent.model_validate(
                        yaml.safe_load(path.read_text(encoding="utf-8"))
                    )
                )
            except (OSError, ValueError, yaml.YAMLError) as exc:
                raise MemoryVaultError(f"invalid memory review event {path}: {exc}") from exc
        return events

    def _effective(self, document: MemoryDocument) -> MemoryDocument:
        envelope = document.envelope
        for event in self.history_for(document):
            if event.memory_id != envelope.id or event.from_status != envelope.status:
                raise MemoryVaultError(
                    f"review history chain is invalid for {document.envelope.id}"
                )
            envelope = self._apply_review_event(envelope, event)
        return document.model_copy(update={"envelope": envelope})

    @staticmethod
    def _apply_review_event(
        envelope: MemoryEnvelope,
        event: MemoryReviewEvent,
    ) -> MemoryEnvelope:
        data = envelope.model_dump(by_alias=True, mode="python")
        data["status"] = event.to_status
        data["updated_at"] = event.created_at
        data["reviewed_by"] = event.reviewer
        if event.to_status == MemoryStatus.ACCEPTED:
            data["trust"] = TrustLevel.HUMAN_REVIEWED
            if event.metadata is not None:
                metadata = event.metadata
                if metadata.applies_when is not None:
                    data["applies_when"] = metadata.applies_when.model_dump()
                if metadata.evidence is not None:
                    data["evidence"] = [item.model_dump() for item in metadata.evidence]
                if metadata.relations is not None:
                    data["relations"] = metadata.relations.model_dump()
                if metadata.validity is not None:
                    data["validity"] = metadata.validity.model_dump()
        if event.to_status == MemoryStatus.SUPERSEDED:
            relations = envelope.relations.model_dump(mode="python")
            relations["superseded_by"] = [event.replacement_id]
            data["relations"] = relations
        return MemoryEnvelope.model_validate(data)

    def append_review(self, event: MemoryReviewEvent) -> Path:
        document = self.read(event.memory_id)
        if document.envelope.status != event.from_status:
            raise MemoryVaultError("review event does not continue current state")
        self._apply_review_event(document.envelope, event)
        root = self._events_root(document)
        root.mkdir(parents=True, exist_ok=True)
        timestamp = event.created_at.strftime("%Y%m%dT%H%M%S%fZ")
        destination = root / f"{timestamp}-{event.event_id}.yaml"
        rendered = yaml.safe_dump(
            event.model_dump(by_alias=True, mode="json"),
            sort_keys=False,
            allow_unicode=True,
        )
        try:
            with destination.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
        except FileExistsError as exc:
            message = f"review event already exists: {event.event_id}"
            raise MemoryAlreadyExistsError(message) from exc
        return destination

    def review_event_id(self, payload: str) -> str:
        return f"rev_{hashlib.sha256(payload.encode()).hexdigest()[:24]}"

    def _matches_project(self, document: MemoryDocument) -> bool:
        return document.envelope.project == self.project or (
            document.envelope.scope == MemoryScope.USER and document.envelope.project == "*"
        )

    def read(self, memory_id: str, *, include_user: bool = True) -> MemoryDocument:
        for document in self.documents(include_user=include_user):
            if document.envelope.id == memory_id:
                return document
        raise KeyError(memory_id)

    def search(
        self,
        query: str,
        *,
        project: str | None = None,
        limit: int = 10,
        include_user: bool = False,
    ) -> list[MemoryDocument]:
        if project is not None and project != self.project:
            raise MemoryIsolationError("search project must match repository project")
        terms = set(re.findall(r"\w+", query.casefold()))
        ranked: list[tuple[int, MemoryDocument]] = []
        for document in self.documents(include_user=include_user):
            if document.envelope.status in _EXCLUDED_STATUSES:
                continue
            haystack = " ".join(
                (
                    document.envelope.title,
                    " ".join(document.envelope.tags),
                    document.body,
                    " ".join(document.envelope.applies_when.concepts),
                    " ".join(document.envelope.applies_when.operations),
                )
            ).casefold()
            score = sum(1 for term in terms if term in haystack)
            if score:
                ranked.append((score, document))
        ranked.sort(key=lambda item: (-item[0], item[1].envelope.id))
        return [document for _, document in ranked[:limit]]
