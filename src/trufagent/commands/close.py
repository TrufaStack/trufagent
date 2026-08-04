from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from trufagent.application.close_v2 import CloseV2Service
from trufagent.domain.close_v2 import CloseV2Request
from trufagent.infrastructure.git_merge import GitMergeVerifier
from trufagent.infrastructure.graphify_adapter import GraphifyAdapter, GraphifyAdapterError
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository, MemoryVaultError
from trufagent.infrastructure.memory_index import SqliteMemoryIndex
from trufagent.infrastructure.memory_v2_fs import MarkdownMemoryRepositoryV2


def run(args, *, project_resolver) -> int:
    try:
        project = project_resolver(args.project_root, args.project)
        repository = MarkdownMemoryRepository(
            args.project_root,
            project=project,
            user_memory_root=Path.home() / ".trufagent" / "memory" / "user",
        ).initialize()
        request = CloseV2Request.model_validate_json(
            args.request.read_text(encoding="utf-8")
        )
        result = CloseV2Service(
            MarkdownMemoryRepositoryV2(
                args.project_root, project=project
            ).initialize(),
            repository,
            SqliteMemoryIndex(
                Path(args.project_root) / ".trufagent" / "memory-index.sqlite3"
            ),
            GitMergeVerifier(),
            GraphifyAdapter(),
            project=project,
        ).close(args.project_root, request)
    except (
        OSError,
        ValueError,
        ValidationError,
        GraphifyAdapterError,
        MemoryVaultError,
    ) as exc:
        print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
        return 1
    print(result.model_dump_json(by_alias=True))
    return 0
