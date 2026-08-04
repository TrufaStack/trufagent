from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from trufagent.application.prepare_v2 import PrepareV2Service
from trufagent.application.task_extractor import TaskIntake
from trufagent.infrastructure.graphify_adapter import GraphifyAdapter
from trufagent.infrastructure.memory_combined import CombinedMemoryRepository
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository, MemoryVaultError
from trufagent.infrastructure.memory_v2_fs import MarkdownMemoryRepositoryV2
from trufagent.infrastructure.model_profiles import Harness


def run(args, *, project_resolver, catalog_loader) -> int:
    try:
        project = project_resolver(args.project_root, args.project)
        intake = TaskIntake.model_validate_json(args.intake.read_text(encoding="utf-8"))
        repository = MarkdownMemoryRepository(
            args.project_root,
            project=project,
            user_memory_root=Path.home() / ".trufagent" / "memory" / "user",
        ).initialize()
        result = PrepareV2Service(
            CombinedMemoryRepository(
                repository,
                MarkdownMemoryRepositoryV2(
                    args.project_root, project=project
                ).initialize(),
            ),
            cartography=GraphifyAdapter(),
            skills=catalog_loader(args.project_root, args.catalog),
        ).prepare(
            intake,
            project=project,
            project_root=args.project_root,
            harness=Harness(args.harness).value if args.harness else None,
        )
    except (OSError, ValueError, ValidationError, MemoryVaultError) as exc:
        print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
        return 1
    print(result.model_dump_json(by_alias=True))
    return 0
