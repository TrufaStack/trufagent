from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field

from trufagent.domain.skills import SkillCatalogDocument

_BEGIN = "# BEGIN TRUFAGENT MANAGED SKILL SURFACE"
_END = "# END TRUFAGENT MANAGED SKILL SURFACE"


class CodexSkillSurface(BaseModel):
    daily: list[str] = Field(default_factory=list)
    library: list[str] = Field(default_factory=list)
    disabled_paths: list[Path] = Field(default_factory=list)


def plan_codex_skill_surface(
    catalog: SkillCatalogDocument,
    codex_skill_root: Path,
    *,
    core_names: set[str] | None = None,
) -> CodexSkillSurface:
    root = Path(codex_skill_root).resolve()
    core = core_names or {"trufagent", "start-session", "end-session"}
    reviewed_paths = {
        Path(location.path).resolve()
        for entry in catalog.entries
        if entry.reviewed and entry.active and entry.available
        for location in entry.locations
        if location.platform == "codex"
    }
    daily: list[str] = []
    library: list[str] = []
    disabled: list[Path] = []
    for skill_file in sorted(root.glob("*/SKILL.md")):
        resolved = skill_file.resolve()
        name = skill_file.parent.name
        if name in core or resolved in reviewed_paths:
            daily.append(name)
        else:
            library.append(name)
            disabled.append(resolved)
    return CodexSkillSurface(
        daily=daily,
        library=library,
        disabled_paths=disabled,
    )


def render_managed_skill_surface(surface: CodexSkillSurface) -> str:
    lines = [_BEGIN]
    for path in surface.disabled_paths:
        escaped = str(path).replace("\\", "\\\\").replace('"', '\\"')
        lines.extend(
            [
                "[[skills.config]]",
                f'path = "{escaped}"',
                "enabled = false",
                "",
            ]
        )
    lines.append(_END)
    return "\n".join(lines)


def apply_managed_skill_surface(config_path: Path, surface: CodexSkillSurface) -> Path:
    path = Path(config_path)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if (_BEGIN in existing) != (_END in existing):
        raise ValueError("incomplete Trufagent managed skill surface block")
    if _BEGIN in existing:
        prefix, remainder = existing.split(_BEGIN, 1)
        _, suffix = remainder.split(_END, 1)
        existing = prefix.rstrip() + suffix
    rendered = existing.rstrip() + "\n\n" + render_managed_skill_surface(surface) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path
