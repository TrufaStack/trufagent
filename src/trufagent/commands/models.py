from __future__ import annotations

import json
import sys

import yaml
from pydantic import ValidationError

from trufagent.domain.task import ModelTier
from trufagent.infrastructure.model_profiles import Harness, resolve_project_model


def run(args) -> int:
    try:
        result = resolve_project_model(
            args.project_root,
            Harness(args.harness),
            ModelTier(args.tier),
        )
    except (OSError, ValueError, ValidationError, yaml.YAMLError) as exc:
        print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
        return 1
    print(result.model_dump_json())
    return 0
