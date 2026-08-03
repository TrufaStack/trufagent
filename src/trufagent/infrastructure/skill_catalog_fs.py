from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml

from trufagent.domain.skills import SkillCatalogDocument


def _host_families(entry) -> set[str]:
    return {
        location.platform.split(":", 1)[0].split("-", 1)[0]
        for location in entry.locations
    }


class SkillCatalogRepository:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> SkillCatalogDocument:
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        return SkillCatalogDocument.model_validate(raw)

    def save(self, catalog: SkillCatalogDocument) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = catalog.model_dump(by_alias=True, mode="json")
        rendered = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)
        return self.path

    def sync(self, discovered: SkillCatalogDocument) -> SkillCatalogDocument:
        existing = self.load() if self.path.is_file() else None
        reviews = (
            {(entry.name, entry.fingerprint): entry.reviewed for entry in existing.entries}
            if existing
            else {}
        )
        active_choices = (
            {
                (entry.name, entry.fingerprint)
                for entry in existing.entries
                if entry.active and entry.reviewed
            }
            if existing
            else {}
        )
        quarantined = (
            {(entry.name, entry.fingerprint) for entry in existing.entries if entry.quarantined}
            if existing
            else set()
        )
        for entry in discovered.entries:
            entry.reviewed = reviews.get((entry.name, entry.fingerprint), False)
            entry.quarantined = (entry.name, entry.fingerprint) in quarantined
            if entry.quarantined:
                entry.active = False
            if (entry.name, entry.fingerprint) in active_choices:
                entry.active = not entry.quarantined
        self.save(discovered)
        return discovered

    def review(self, entry_id: str, *, activate: bool = False) -> SkillCatalogDocument:
        catalog = self.load()
        selected = next((entry for entry in catalog.entries if entry.id == entry_id), None)
        if selected is None:
            raise KeyError(entry_id)
        if activate:
            selected_families = _host_families(selected)
            for entry in catalog.entries:
                if entry.name == selected.name and selected_families & _host_families(entry):
                    entry.active = entry.id == selected.id
        selected.reviewed = True
        self.save(catalog)
        return catalog
