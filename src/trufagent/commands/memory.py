from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from trufagent.application.memory_review import MemoryReviewService
from trufagent.application.memory_v2 import MemoryV2Service
from trufagent.domain.memory import MemoryReviewMetadata
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository, MemoryVaultError
from trufagent.infrastructure.memory_index import SqliteMemoryIndex
from trufagent.infrastructure.memory_markdown import (
    MemoryFormatError,
    load_memory_markdown,
    load_memory_markdown_compatible,
)
from trufagent.infrastructure.memory_v2_fs import MarkdownMemoryRepositoryV2


def _validate(args) -> int:
    try:
        document = load_memory_markdown_compatible(args.path)
    except (OSError, MemoryFormatError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "success",
                "summary": f"valid memory: {document.envelope.id}",
                "next_actions": [],
                "artifacts": [str(args.path)],
            }
        )
    )
    return 0


def _propose(args) -> int:
    repository = MarkdownMemoryRepository(
        args.project_root,
        project=args.project,
        user_memory_root=Path.home() / ".trufagent" / "memory" / "user",
    ).initialize()
    try:
        raw = args.document.read_text(encoding="utf-8")
        parts = raw.split("---", 2)
        if len(parts) != 3:
            raise MemoryFormatError("expected YAML frontmatter delimited by ---")
        frontmatter = yaml.safe_load(parts[1])
        if not isinstance(frontmatter, dict):
            raise MemoryFormatError("frontmatter must be a YAML mapping")
        if frontmatter.get("schema") == "trufagent.memory.v2":
            document = load_memory_markdown_compatible(args.document)
            v2_repository = MarkdownMemoryRepositoryV2(
                args.project_root, project=args.project
            ).initialize()
            path = v2_repository.propose(document)
            SqliteMemoryIndex(
                Path(args.project_root) / ".trufagent" / "memory-index.sqlite3"
            ).rebuild([*repository.documents(), *v2_repository.documents()])
        else:
            document = load_memory_markdown(args.document)
            if document.envelope.status.value != "proposed":
                raise ValueError("memory propose requires status proposed")
            path = repository.propose(document)
    except (
        OSError,
        ValueError,
        MemoryFormatError,
        MemoryVaultError,
        yaml.YAMLError,
    ) as exc:
        print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"status": "proposed", "memory_id": document.envelope.id, "path": str(path)}
        )
    )
    return 0


def run(args) -> int:
    if args.memory_command == "validate":
        return _validate(args)
    if args.memory_command == "propose":
        return _propose(args)

    repository = MarkdownMemoryRepository(
        args.project_root,
        project=args.project,
        user_memory_root=Path.home() / ".trufagent" / "memory" / "user",
    ).initialize()
    index = SqliteMemoryIndex(
        Path(args.project_root) / ".trufagent" / "memory-index.sqlite3"
    )
    review = MemoryReviewService(repository, index=index)
    v2_repository = MarkdownMemoryRepositoryV2(
        args.project_root, project=args.project
    ).initialize()
    review_v2 = MemoryV2Service(
        v2_repository,
        index=index,
        legacy_documents=repository.documents,
    )
    try:
        if args.memory_command == "list":
            documents = [*repository.documents(), *v2_repository.documents()]
            if args.status:
                documents = [
                    document
                    for document in documents
                    if document.envelope.status.value == args.status
                ]
            print(
                json.dumps(
                    [
                        {
                            "id": document.envelope.id,
                            "title": document.envelope.title,
                            "kind": document.envelope.kind.value,
                            "status": document.envelope.status.value,
                            "governs": document.envelope.governs_behavior,
                        }
                        for document in documents
                    ]
                )
            )
        elif args.memory_command == "show":
            try:
                document = v2_repository.read(args.memory_id)
            except KeyError:
                document = repository.read(args.memory_id)
            print(document.model_dump_json())
        elif args.memory_command == "history":
            try:
                events = v2_repository.events(args.memory_id)
                v2_repository.read(args.memory_id)
            except KeyError:
                events = review.history(args.memory_id)
            print(
                json.dumps(
                    [event.model_dump(by_alias=True, mode="json") for event in events]
                )
            )
        elif args.memory_command == "accept":
            try:
                v2_repository.read(args.memory_id)
            except KeyError:
                metadata = (
                    MemoryReviewMetadata.model_validate_json(
                        args.metadata.read_text(encoding="utf-8")
                    )
                    if args.metadata
                    else None
                )
                result = review.accept(
                    args.memory_id,
                    reviewer=args.reviewer,
                    metadata=metadata,
                )
            else:
                if args.metadata:
                    raise ValueError("v2 accept does not use extended metadata")
                result = review_v2.accept(args.memory_id, reviewer=args.reviewer)
            print(result.model_dump_json())
        elif args.memory_command == "replace":
            print(
                review_v2.replace(
                    args.memory_id,
                    replacement_id=args.replacement_id,
                    reviewer=args.reviewer,
                    reason=args.reason,
                ).model_dump_json()
            )
        elif args.memory_command == "retire":
            print(
                review_v2.retire(
                    args.memory_id,
                    reviewer=args.reviewer,
                    reason=args.reason,
                ).model_dump_json()
            )
        elif args.memory_command == "reject":
            print(
                review.reject(
                    args.memory_id,
                    reviewer=args.reviewer,
                    reason=args.reason,
                ).model_dump_json()
            )
        else:
            print(
                review.supersede(
                    args.memory_id,
                    replacement_id=args.replacement_id,
                    reviewer=args.reviewer,
                    reason=args.reason,
                ).model_dump_json()
            )
    except (OSError, KeyError, ValueError, MemoryVaultError) as exc:
        print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
        return 1
    return 0
