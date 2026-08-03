from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trufagent.domain.skill_import import SkillImportItem, SkillImportManifest
from trufagent.domain.skill_sources import RemoteSkillRegistry


def _parse_selector(selector: str) -> tuple[str, str]:
    try:
        repository, skill = selector.rsplit(":", 1)
    except ValueError as exc:
        raise ValueError(f"invalid skill selector: {selector!r}") from exc
    if repository.count("/") != 1 or not skill:
        raise ValueError(f"invalid skill selector: {selector!r}")
    return repository, skill


def plan_skill_import(
    registry: RemoteSkillRegistry,
    *,
    direct: list[str],
    adapt: list[str],
    vendor_root: Path,
    adaptation_root: Path,
) -> SkillImportManifest:
    sources = {source.repository.lower(): source for source in registry.sources}
    items: list[SkillImportItem] = []
    for mode, selectors in (("direct", direct), ("adapt", adapt)):
        for selector in selectors:
            repository_name, skill_name = _parse_selector(selector)
            source = sources.get(repository_name.lower())
            if source is None:
                raise ValueError(f"repository is not in the governed registry: {repository_name}")
            candidates = [skill for skill in source.skills if skill.name == skill_name]
            if len(candidates) != 1:
                raise ValueError(
                    f"expected one skill {skill_name!r} in {source.repository}, "
                    f"found {len(candidates)}"
                )
            skill = candidates[0]
            findings = sorted({finding.code for finding in skill.findings})
            reasons: list[str] = []
            if skill.local_duplicate:
                status = "rejected"
                reasons.append("exact-local-duplicate")
            elif any(finding.severity == "critical" for finding in skill.findings):
                status = "needs-review"
                reasons.append("critical-static-signal")
            elif source.license is None:
                status = "needs-review"
                reasons.append("repository-license-not-declared")
            else:
                status = "candidate"
                reasons.append("pinned-source-and-no-critical-signal")
            destination = (
                vendor_root / source.repository / source.head_sha / skill.name
                if mode == "direct"
                else adaptation_root / skill.name
            )
            items.append(
                SkillImportItem(
                    repository=source.repository,
                    commit=source.head_sha,
                    license=source.license,
                    source_name=skill.name,
                    source_path=skill.path,
                    source_fingerprint=skill.fingerprint,
                    mode=mode,
                    destination=str(destination),
                    local_duplicate=skill.local_duplicate,
                    findings=findings,
                    status=status,
                    reasons=reasons,
                )
            )
    return SkillImportManifest(generated_at=datetime.now(UTC), items=items)
