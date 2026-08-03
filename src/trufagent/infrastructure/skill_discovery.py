from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from trufagent.domain.skills import (
    SkillCatalogDocument,
    SkillCatalogEntry,
    SkillLocation,
)

_FRONTMATTER = re.compile(r"\A---\s*\n(?P<yaml>.*?)\n---(?:\s*\n|\Z)", re.DOTALL)
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")
_MAX_SKILL_BYTES = 2_000_000


class SkillDiscoveryResult(BaseModel):
    catalog: SkillCatalogDocument
    warnings: list[str] = Field(default_factory=list)


class SkillDiscovery:
    def __init__(
        self,
        roots: dict[str, Path],
        *,
        root_metadata: dict[str, tuple[str, str]] | None = None,
    ) -> None:
        self.roots = {platform: Path(root).resolve() for platform, root in roots.items()}
        self.root_metadata = root_metadata or {}

    @staticmethod
    def _metadata(path: Path, content: bytes) -> tuple[str, str, str, str]:
        text = content.decode("utf-8")
        match = _FRONTMATTER.match(text)
        try:
            raw = yaml.safe_load(match.group("yaml")) if match else {}
        except yaml.YAMLError:
            raw = {}
        raw = raw if isinstance(raw, dict) else {}
        name = str(raw.get("name") or path.parent.name)
        description = str(raw.get("description") or "")
        source = str(raw.get("source") or raw.get("repository") or "local-discovery")
        version_file = path.parent / ".graphify_version"
        version = str(raw.get("version") or "")
        if not version and version_file.is_file():
            version = version_file.read_text(encoding="utf-8").strip()
        return name, description, source, version or "unknown"

    def scan(self) -> SkillDiscoveryResult:
        grouped: dict[tuple[str, str], SkillCatalogEntry] = {}
        warnings: list[str] = []
        for platform, root in sorted(self.roots.items()):
            if not root.is_dir():
                warnings.append(f"skill root for {platform!r} does not exist: {root}")
                continue
            for path in sorted(root.rglob("SKILL.md")):
                resolved = path.resolve()
                if not resolved.is_relative_to(root):
                    warnings.append(f"ignored skill outside root via symlink: {path}")
                    continue
                try:
                    size = resolved.stat().st_size
                    if size > _MAX_SKILL_BYTES:
                        warnings.append(f"ignored oversized skill: {resolved}")
                        continue
                    content = resolved.read_bytes()
                    name, description, source, skill_version = self._metadata(resolved, content)
                    root_source, root_version = self.root_metadata.get(
                        platform, ("local-discovery", "unknown")
                    )
                    if source == "local-discovery":
                        source = root_source
                    if skill_version == "unknown":
                        skill_version = root_version
                except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
                    warnings.append(f"cannot inspect {resolved}: {exc}")
                    continue
                fingerprint = hashlib.sha256(content).hexdigest()
                key = (name, fingerprint)
                location = SkillLocation(platform=platform, path=str(resolved))
                if key in grouped:
                    grouped[key].locations.append(location)
                else:
                    safe_name = _SAFE_NAME.sub("-", name).strip("-") or "skill"
                    grouped[key] = SkillCatalogEntry(
                        id=f"{safe_name}@{fingerprint[:12]}",
                        name=name,
                        description=description,
                        source=source,
                        version=skill_version,
                        fingerprint=fingerprint,
                        locations=[location],
                    )

        by_name: dict[str, list[SkillCatalogEntry]] = defaultdict(list)
        for entry in grouped.values():
            by_name[entry.name].append(entry)
        for name, variants in by_name.items():
            if len(variants) > 1:
                for variant in variants:
                    variant.active = False
                warnings.append(f"skill {name!r} has {len(variants)} different installed variants")

        return SkillDiscoveryResult(
            catalog=SkillCatalogDocument(
                schema="trufagent.skills.v1",
                generated_at=datetime.now(UTC),
                entries=sorted(grouped.values(), key=lambda item: (item.name, item.fingerprint)),
            ),
            warnings=warnings,
        )


def default_skill_roots(home: Path) -> tuple[dict[str, Path], dict[str, tuple[str, str]]]:
    home = Path(home).resolve()
    roots = {
        "claude": home / ".claude" / "skills",
        "codex": home / ".codex" / "skills",
    }
    metadata = {
        "claude": ("local:claude-skills", "unknown"),
        "codex": ("local:codex-skills", "unknown"),
    }
    registry = home / ".claude" / "plugins" / "installed_plugins.json"
    if not registry.is_file() or registry.stat().st_size > 2_000_000:
        return roots, metadata
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return roots, metadata
    plugins = payload.get("plugins", {}) if isinstance(payload, dict) else {}
    if not isinstance(plugins, dict):
        return roots, metadata
    for plugin_name, installations in plugins.items():
        if not isinstance(installations, list):
            continue
        for index, installation in enumerate(installations):
            if not isinstance(installation, dict) or not installation.get("installPath"):
                continue
            platform = f"claude-plugin:{plugin_name}:{index}"
            roots[platform] = Path(str(installation["installPath"])) / "skills"
            metadata[platform] = (
                f"claude-plugin:{plugin_name}",
                str(installation.get("version") or "unknown"),
            )
    return roots, metadata
