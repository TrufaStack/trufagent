from __future__ import annotations

import json
import sys

from trufagent.infrastructure.graphify_adapter import GraphifyAdapter, GraphifyAdapterError


def run(args) -> int:
    cartography = GraphifyAdapter()
    try:
        if args.graph_command == "status":
            result = cartography.status(args.project_root)
        elif args.graph_command == "update":
            result = cartography.update(args.project_root)
        elif args.graph_command == "query":
            result = cartography.query(
                args.project_root, args.question, token_budget=args.budget
            )
        else:
            result = cartography.affected(
                args.project_root,
                args.label,
                relations=args.relation,
                depth=args.depth,
            )
    except (OSError, GraphifyAdapterError) as exc:
        print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
        return 1
    print(result.model_dump_json())
    return 0
