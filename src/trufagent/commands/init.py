from __future__ import annotations

import json
import sys

from trufagent.infrastructure.memory_fs import MemoryVaultError
from trufagent.infrastructure.project_init import ProjectInitializationError, initialize_project


def run(args) -> int:
    try:
        config = initialize_project(
            args.project_root,
            project=args.project,
            catalog_path=args.catalog,
        )
    except (OSError, ValueError, MemoryVaultError, ProjectInitializationError) as exc:
        print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"status": "success", "config": str(config)}))
    return 0
