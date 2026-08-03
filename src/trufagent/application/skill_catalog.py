from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from trufagent.domain.skills import SkillCatalogDocument


class SkillDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    version: str = Field(min_length=1)
    reviewed: bool = False
    description: str = ""
    fingerprint: str | None = None
    locations: list[str] = Field(default_factory=list)


class SkillSelection(BaseModel):
    selected: list[SkillDescriptor] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class InMemorySkillCatalog:
    def __init__(self, skills: list[SkillDescriptor]) -> None:
        self._skills = {skill.name: skill for skill in skills}

    @classmethod
    def from_document(cls, document: SkillCatalogDocument) -> InMemorySkillCatalog:
        return cls(
            [
                SkillDescriptor(
                    name=entry.name,
                    source=entry.source,
                    version=entry.version,
                    reviewed=entry.reviewed,
                    description=entry.description,
                    fingerprint=entry.fingerprint,
                    locations=[location.path for location in entry.locations],
                )
                for entry in document.entries
                if entry.active and entry.available
            ]
        )

    def select(self, names: list[str]) -> SkillSelection:
        selected: list[SkillDescriptor] = []
        warnings: list[str] = []
        for name in dict.fromkeys(names):
            skill = self._skills.get(name)
            if skill is None:
                warnings.append(f"skill {name!r} is not installed in the active catalog")
            elif not skill.reviewed:
                warnings.append(f"skill {name!r} is installed but not reviewed")
            else:
                selected.append(skill)
        return SkillSelection(selected=selected, warnings=warnings)
