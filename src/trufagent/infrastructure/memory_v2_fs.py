from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from trufagent.domain.memory_v2 import (
    MemoryActionV2,
    MemoryDocumentV2,
    MemoryEnvelopeV2,
    MemoryEventV2,
    MemoryStateV2,
)
from trufagent.infrastructure.memory_fs import MemoryAlreadyExistsError, MemoryVaultError
from trufagent.infrastructure.memory_markdown import (
    SecretShapeError,
    find_secret_shapes,
    load_memory_markdown_compatible,
)


def _render(document: MemoryDocumentV2) -> str:
    data = document.envelope.model_dump(by_alias=True, mode="json")
    frontmatter = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{frontmatter}\n---\n{document.body.strip()}\n"


class MarkdownMemoryRepositoryV2:
    """Create-only v2 memory stored beside, but not mixed into, v1 glob reads."""

    def __init__(self, project_root: Path, *, project: str) -> None:
        self.project_root = Path(project_root)
        self.project = project
        self.root = self.project_root / ".trufagent" / "memory" / "project" / "v2"

    def initialize(self) -> MarkdownMemoryRepositoryV2:
        self.root.mkdir(parents=True, exist_ok=True)
        return self

    def propose(self, document: MemoryDocumentV2) -> Path:
        if document.envelope.project != self.project:
            raise MemoryVaultError("v2 memory project does not match repository project")
        if document.envelope.status != MemoryStateV2.PROPOSED:
            raise MemoryVaultError("new v2 memory must be proposed")
        shapes = find_secret_shapes(f"{document.envelope.title}\n{document.body}")
        if shapes:
            raise SecretShapeError(shapes)
        destination = self.root / f"{document.envelope.id}.md"
        try:
            with destination.open("x", encoding="utf-8") as handle:
                handle.write(_render(document))
        except FileExistsError as exc:
            raise MemoryAlreadyExistsError(
                f"memory {document.envelope.id!r} already exists"
            ) from exc
        return destination

    def _events_root(self, memory_id: str) -> Path:
        return self.root / ".events" / memory_id

    def events(self, memory_id: str) -> list[MemoryEventV2]:
        root = self._events_root(memory_id)
        if not root.is_dir():
            return []
        try:
            return [
                MemoryEventV2.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
                for path in sorted(root.glob("*.yaml"))
            ]
        except (OSError, ValueError, yaml.YAMLError) as exc:
            raise MemoryVaultError(f"invalid v2 memory event: {exc}") from exc

    def _effective(self, document: MemoryDocumentV2) -> MemoryDocumentV2:
        envelope = document.envelope
        for event in self.events(envelope.id):
            if event.memory_id != envelope.id:
                raise MemoryVaultError("v2 memory event targets a different memory")
            if event.created_at < envelope.updated_at:
                raise MemoryVaultError("v2 memory event predates current state")
            data = envelope.model_dump(by_alias=True, mode="python")
            data["updated_at"] = event.created_at
            data["reviewed_by"] = event.reviewer
            if event.action == MemoryActionV2.ACCEPT:
                if envelope.status != MemoryStateV2.PROPOSED:
                    raise MemoryVaultError("accept requires proposed memory")
                data["status"] = MemoryStateV2.ACCEPTED
            elif event.action == MemoryActionV2.REPLACE:
                if envelope.status != MemoryStateV2.ACCEPTED:
                    raise MemoryVaultError("replace requires accepted memory")
                data["status"] = MemoryStateV2.REPLACED
            else:
                if envelope.status not in {MemoryStateV2.PROPOSED, MemoryStateV2.ACCEPTED}:
                    raise MemoryVaultError("retire requires active memory")
                data["status"] = MemoryStateV2.RETIRED
            envelope = MemoryEnvelopeV2.model_validate(data)
        return document.model_copy(update={"envelope": envelope})

    def documents(self) -> list[MemoryDocumentV2]:
        return [
            self._effective(load_memory_markdown_compatible(path))
            for path in sorted(self.root.glob("*.md"))
        ]

    def read(self, memory_id: str) -> MemoryDocumentV2:
        for document in self.documents():
            if document.envelope.id == memory_id:
                return document
        raise KeyError(memory_id)

    def append(self, event: MemoryEventV2) -> Path:
        current = self.read(event.memory_id)
        if (
            event.action == MemoryActionV2.ACCEPT
            and current.envelope.status != MemoryStateV2.PROPOSED
        ):
            raise ValueError("accept requires proposed memory")
        if event.action == MemoryActionV2.REPLACE:
            if current.envelope.status != MemoryStateV2.ACCEPTED:
                raise ValueError("replace requires accepted memory")
            replacement = self.read(event.replacement_id or "")
            if replacement.envelope.status != MemoryStateV2.ACCEPTED:
                raise ValueError("replacement memory must be accepted")
        if event.action == MemoryActionV2.RETIRE and current.envelope.status not in {
            MemoryStateV2.PROPOSED,
            MemoryStateV2.ACCEPTED,
        }:
            raise ValueError("retire requires active memory")
        root = self._events_root(event.memory_id)
        root.mkdir(parents=True, exist_ok=True)
        stamp = event.created_at.strftime("%Y%m%dT%H%M%S%fZ")
        destination = root / f"{stamp}-{event.event_id}.yaml"
        payload = yaml.safe_dump(event.model_dump(by_alias=True, mode="json"), sort_keys=False)
        try:
            with destination.open("x", encoding="utf-8") as handle:
                handle.write(payload)
        except FileExistsError as exc:
            raise MemoryAlreadyExistsError(f"event {event.event_id!r} already exists") from exc
        return destination

    @staticmethod
    def event_id(payload: str) -> str:
        return f"rev_{hashlib.sha256(payload.encode()).hexdigest()[:24]}"
