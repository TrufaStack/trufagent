from pathlib import Path

import pytest
import yaml

from trufagent.infrastructure.project_init import ProjectInitializationError, initialize_project


def test_project_init_creates_vault_and_tracked_config(tmp_path: Path) -> None:
    catalog = tmp_path / "user" / "catalog.yaml"

    config_path = initialize_project(tmp_path / "repo", project="demo", catalog_path=catalog)

    data = yaml.safe_load(config_path.read_text())
    assert data["schema"] == "trufagent.project.v1"
    assert data["project"] == "demo"
    assert data["skills"]["catalog"] == str(catalog)
    assert (tmp_path / "repo" / ".trufagent" / "memory" / "project").is_dir()


def test_project_init_is_idempotent_but_refuses_different_config(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    catalog = tmp_path / "catalog.yaml"
    first = initialize_project(root, project="demo", catalog_path=catalog)
    second = initialize_project(root, project="demo", catalog_path=catalog)

    assert first == second
    with pytest.raises(ProjectInitializationError, match="already exists"):
        initialize_project(root, project="other", catalog_path=catalog)
