from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from trufagent.domain.skills import SkillCatalogDocument, SkillLocation

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return {token for token in _TOKEN.findall(value.lower()) if len(token) > 2}


def _platform_matches(platform: str, harness: str) -> bool:
    return platform == harness or platform.startswith(f"{harness}-") or platform.startswith(
        f"{harness}:"
    )


class SkillDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    version: str = Field(min_length=1)
    reviewed: bool = False
    description: str = ""
    fingerprint: str | None = None
    locations: list[SkillLocation] = Field(default_factory=list)

    def location_for(self, harness: str | None = None) -> SkillLocation | None:
        if harness is not None:
            exact = next(
                (
                    location
                    for location in self.locations
                    if _platform_matches(location.platform, harness)
                ),
                None,
            )
            if exact is not None:
                return exact
        return self.locations[0] if self.locations else None


class SkillMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: SkillDescriptor
    score: int = Field(ge=0)
    matched_terms: list[str] = Field(default_factory=list)
    location: SkillLocation | None = None


class SkillSelection(BaseModel):
    selected: list[SkillDescriptor] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class InMemorySkillCatalog:
    def __init__(self, skills: list[SkillDescriptor]) -> None:
        self._skills: dict[str, list[SkillDescriptor]] = {}
        for skill in skills:
            self._skills.setdefault(skill.name, []).append(skill)

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
                    locations=list(entry.locations),
                )
                for entry in document.entries
                if entry.active and entry.available and not entry.quarantined
            ]
        )

    def select(self, names: list[str], *, harness: str | None = None) -> SkillSelection:
        selected: list[SkillDescriptor] = []
        warnings: list[str] = []
        for name in dict.fromkeys(names):
            candidates = self._skills.get(name, [])
            if not candidates:
                warnings.append(f"skill {name!r} is not installed in the active catalog")
                continue
            reviewed = [skill for skill in candidates if skill.reviewed]
            if not reviewed:
                warnings.append(f"skill {name!r} is installed but not reviewed")
                continue
            compatible = (
                [skill for skill in reviewed if skill.location_for(harness)]
                if harness is not None
                else reviewed
            )
            if not compatible:
                warnings.append(f"skill {name!r} has no location for harness {harness!r}")
                continue
            exact = (
                [
                    skill
                    for skill in compatible
                    if any(
                        _platform_matches(location.platform, harness)
                        for location in skill.locations
                    )
                ]
                if harness is not None
                else compatible
            )
            choices = exact or compatible
            if len(choices) > 1:
                warnings.append(f"skill {name!r} has multiple reviewed active variants")
                continue
            selected.append(choices[0])
        return SkillSelection(selected=selected, warnings=warnings)

    def search(
        self,
        query: str,
        *,
        harness: str | None = None,
        limit: int = 10,
        reviewed_only: bool = True,
    ) -> list[SkillMatch]:
        terms = _tokens(query)
        if not terms or limit < 1:
            return []
        matches: list[SkillMatch] = []
        for variants in self._skills.values():
            for skill in variants:
                if reviewed_only and not skill.reviewed:
                    continue
                name_terms = _tokens(skill.name.replace("-", " "))
                description_terms = _tokens(skill.description)
                name_hits = terms & name_terms
                description_hits = terms & description_terms
                score = len(name_hits) * 5 + len(description_hits)
                if query.lower() == skill.name.lower():
                    score += 20
                if not name_hits and len(description_hits) < 2:
                    continue
                matches.append(
                    SkillMatch(
                        skill=skill,
                        score=score,
                        matched_terms=sorted(name_hits | description_hits),
                        location=skill.location_for(harness),
                    )
                )
        return sorted(matches, key=lambda match: (-match.score, match.skill.name))[:limit]
