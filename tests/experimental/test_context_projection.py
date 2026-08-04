from pathlib import Path

import pytest

from trufagent.application.promotion import ContextProjectionPolicy
from trufagent.experimental.context_projection import (
    ContextProjectionError,
    create_context_projection,
)


def _policy() -> ContextProjectionPolicy:
    return ContextProjectionPolicy(
        excluded_globs=(".env*", "*.pem", "uploads/**", "private-data/**")
    )


def test_projection_copies_safe_text_and_excludes_sensitive_and_generated_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "src").mkdir()
    (source / "src" / "app.py").write_text("print('safe')\n")
    (source / ".env.local").write_text("API_KEY=not-projected\n")
    (source / "node_modules").mkdir()
    (source / "node_modules" / "dependency.js").write_text("ignored\n")
    (source / "asset.bin").write_bytes(b"binary\x00content")

    destination = tmp_path / "projection"
    manifest = create_context_projection(source, destination, _policy())

    assert (destination / "src" / "app.py").read_text() == "print('safe')\n"
    assert not (destination / ".env.local").exists()
    assert not (destination / "node_modules").exists()
    assert not (destination / "asset.bin").exists()
    assert manifest.copied_files == 1
    assert manifest.excluded_files == 3


def test_projection_quarantines_secret_file_without_disclosing_value(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    secret = "sk-abcdefghijklmnop1234"
    (source / "config.txt").write_text(f"token={secret}\n")
    destination = tmp_path / "projection"

    manifest = create_context_projection(source, destination, _policy())

    assert not (destination / "config.txt").exists()
    assert manifest.rejected_secret_files == 1
    assert secret not in manifest.model_dump_json()


def test_projection_rejects_symlinks_instead_of_following_them(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n")
    (source / "link.txt").symlink_to(outside)

    destination = tmp_path / "projection"
    manifest = create_context_projection(source, destination, _policy())

    assert not (destination / "link.txt").exists()
    assert manifest.rejected_symlinks == 1


def test_projection_destination_cannot_be_inside_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()

    with pytest.raises(ContextProjectionError):
        create_context_projection(source, source / ".projection", _policy())
