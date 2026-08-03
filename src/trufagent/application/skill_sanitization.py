from __future__ import annotations

import hashlib
import re
import shutil
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from trufagent.domain.skill_audit import SkillAuditReport
from trufagent.domain.skill_sanitization import (
    SkillSanitizationEntry,
    SkillSanitizationManifest,
)
from trufagent.domain.skills import SkillCatalogDocument, SkillCatalogEntry

_CORE = {
    "trufagent",
    "start-session",
    "end-session",
    "systematic-debugging",
    "brainstorming",
    "safety-guard",
    "implement-with-evidence",
    "review-and-remember",
}
_LEGACY_CANDIDATES = {
    "configure-ecc",
    "continuous-learning-v2",
    "frontend-slides",
    "gateguard",
    "rules-distill",
    "skill-stocktake",
    "subagent-driven-development",
    "tdd-workflow",
}
_CAPABILITIES = {
    "debugging": ("debug", "diagnos", "error", "troubleshoot"),
    "planning": ("plan", "brainstorm", "spec", "requirements", "architecture"),
    "testing": ("test", "tdd", "playwright", "qa", "regression"),
    "review": ("review", "quality", "audit", "verify", "verification"),
    "security": ("security", "safe", "guard", "threat", "vulnerability"),
    "design": ("design", "ui", "ux", "frontend", "slides", "visual"),
    "documentation": ("document", "docs", "adr", "writing", "markdown"),
    "delivery": ("deploy", "release", "shipping", "ci", "workflow"),
    "data-ml": ("data", "database", "ml", "model", "huggingface", "analytics"),
    "mobile": ("android", "ios", "flutter", "mobile", "swift"),
    "agent-meta": ("agent", "skill", "memory", "context", "session", "mcp"),
}


def _capability(entry: SkillCatalogEntry) -> str:
    text = f"{entry.name} {entry.description}".lower()
    tokens = set(re.findall(r"[a-z0-9]+", text))
    for capability, needles in _CAPABILITIES.items():
        if any(
            token == needle or (len(needle) >= 4 and token.startswith(needle))
            for needle in needles
            for token in tokens
        ):
            return capability
    return "specialized"


def _rank(entry: SkillCatalogEntry, audit_score: int) -> tuple[int, int, int, str]:
    return (int(entry.reviewed), int(entry.active), audit_score, entry.fingerprint)


def _host_families(entry: SkillCatalogEntry) -> set[str]:
    return {
        location.platform.split(":", 1)[0].split("-", 1)[0]
        for location in entry.locations
    }


def plan_skill_sanitization(
    catalog: SkillCatalogDocument,
    audit: SkillAuditReport,
    *,
    archive_root: Path,
) -> SkillSanitizationManifest:
    audits = {entry.entry_id: entry for entry in audit.entries}
    by_name_and_host: dict[tuple[str, str], list[SkillCatalogEntry]] = defaultdict(list)
    for entry in catalog.entries:
        for family in _host_families(entry):
            by_name_and_host[(entry.name, family)].append(entry)
    canonical_ids = {
        max(
            variants,
            key=lambda entry: _rank(entry, audits.get(entry.id).score if entry.id in audits else 0),
        ).id
        for variants in by_name_and_host.values()
    }
    planned: list[SkillSanitizationEntry] = []
    for entry in catalog.entries:
        result = audits.get(entry.id)
        reasons: list[str] = []
        if entry.name in _CORE and entry.reviewed:
            tier = "core"
            reasons.append("reviewed-essential-capability")
        elif entry.reviewed:
            tier = "profile"
            reasons.append("reviewed-specialized-capability")
        elif entry.quarantined:
            tier = "quarantine"
            reasons.append("persistent-plugin-quarantine")
        elif not entry.active:
            tier = "quarantine"
            reasons.append("inactive-name-conflict")
        elif entry.name in _LEGACY_CANDIDATES:
            tier = "quarantine"
            reasons.append("v1-behavior-candidate")
        elif result is not None and result.disposition == "blocked":
            tier = "quarantine"
            reasons.append("unreviewed-critical-static-signal")
        else:
            tier = "cold"
            reasons.append("not-yet-reviewed")
        canonical = entry.id in canonical_ids
        if not canonical:
            reasons.append("non-canonical-same-name-variant")
        action = "archive" if tier == "quarantine" else (
            "keep-cold" if tier == "cold" else "keep-active"
        )
        planned.append(
            SkillSanitizationEntry(
                entry_id=entry.id,
                name=entry.name,
                fingerprint=entry.fingerprint,
                capability=_capability(entry),
                tier=tier,
                canonical_for_host=canonical,
                reviewed=entry.reviewed,
                active=entry.active,
                reasons=reasons,
                current_locations=[location.path for location in entry.locations],
                proposed_action=action,
                proposed_archive_root=str(archive_root) if action == "archive" else None,
            )
        )
    return SkillSanitizationManifest(
        generated_at=datetime.now(UTC),
        catalog_generated_at=catalog.generated_at,
        audit_generated_at=audit.generated_at,
        entries=planned,
    )


def apply_skill_sanitization(
    manifest: SkillSanitizationManifest,
    catalog: SkillCatalogDocument,
    *,
    movable_roots: list[Path],
) -> dict[str, int]:
    roots = [root.resolve() for root in movable_roots]
    catalog_entries = {entry.id: entry for entry in catalog.entries}
    moved = 0
    quarantined = 0
    for planned in manifest.entries:
        if planned.proposed_action != "archive":
            continue
        entry = catalog_entries.get(planned.entry_id)
        if entry is None or entry.fingerprint != planned.fingerprint:
            raise ValueError(f"catalog entry changed since plan: {planned.entry_id}")
        entry.quarantined = True
        entry.active = False
        quarantined += 1
        archive_root = Path(planned.proposed_archive_root or "").resolve()
        for location in entry.locations:
            source_file = Path(location.path).resolve()
            source_dir = source_file.parent
            if "plugin" in location.platform:
                continue
            if not any(source_dir.is_relative_to(root) for root in roots):
                raise ValueError(f"refusing to move skill outside configured roots: {source_dir}")
            target = archive_root / location.platform / f"{entry.name}@{entry.fingerprint[:12]}"
            if target.exists():
                archived_skill = target / "SKILL.md"
                archived_fingerprint = (
                    hashlib.sha256(archived_skill.read_bytes()).hexdigest()
                    if archived_skill.is_file()
                    else ""
                )
                if not source_dir.exists() and archived_fingerprint == entry.fingerprint:
                    continue
                raise ValueError(f"archive target already exists: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_dir), str(target))
            moved += 1
    return {"moved": moved, "quarantined": quarantined}
