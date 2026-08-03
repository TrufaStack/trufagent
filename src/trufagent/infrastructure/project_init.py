from __future__ import annotations

from pathlib import Path

import yaml

from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository


class ProjectInitializationError(RuntimeError):
    pass


def initialize_project(project_root: Path, *, project: str, catalog_path: Path) -> Path:
    root = Path(project_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    MarkdownMemoryRepository(root, project=project).initialize()
    config_path = root / ".trufagent" / "config.yaml"
    data = {
        "schema": "trufagent.project.v1",
        "project": project,
        "skills": {"catalog": str(Path(catalog_path).resolve())},
        "cartography": {"required": True},
    }
    rendered = yaml.safe_dump(data, sort_keys=False)
    if config_path.exists():
        if config_path.read_text(encoding="utf-8") != rendered:
            raise ProjectInitializationError(
                f"{config_path} already exists with different configuration"
            )
        return config_path
    config_path.write_text(rendered, encoding="utf-8")
    return config_path
