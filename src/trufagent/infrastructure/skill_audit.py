from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from trufagent.domain.skill_audit import (
    SkillAuditEntry,
    SkillAuditFinding,
    SkillAuditReport,
)
from trufagent.domain.skills import SkillCatalogDocument

_CRITICAL = {
    "destructive-command": re.compile(r"\brm\s+-[^\n]*r[^\n]*f\b|\bmkfs\b", re.I),
    "credential-access": re.compile(
        r"\.ssh/(?:id_|config)|\.aws/credentials|\.config/gcloud/credentials", re.I
    ),
    "remote-shell": re.compile(r"(?:curl|wget)[^\n|]{0,200}\|\s*(?:ba)?sh\b", re.I),
}
_WARNINGS = {
    "privilege-escalation": re.compile(r"\bsudo\b", re.I),
    "network-command": re.compile(r"\b(?:curl|wget|Invoke-WebRequest)\b", re.I),
    "sensitive-config": re.compile(r"\.env\b|api[_ -]?key|access[_ -]?token", re.I),
    "instruction-override": re.compile(
        r"ignore (?:all |any )?(?:previous|prior|system) instructions", re.I
    ),
}
_SCRIPT_SUFFIXES = {".py", ".sh", ".bash", ".ps1", ".js", ".ts", ".rb"}
_MAX_FILES = 250
_MAX_SCAN_BYTES = 4_000_000


def _finding(severity: str, code: str, message: str) -> SkillAuditFinding:
    return SkillAuditFinding(severity=severity, code=code, message=message)  # type: ignore[arg-type]


def scan_skill_text(content: str, *, label: str) -> list[SkillAuditFinding]:
    findings: list[SkillAuditFinding] = []
    for code, pattern in _CRITICAL.items():
        if pattern.search(content):
            findings.append(_finding("critical", code, f"Signal found in {label}"))
    for code, pattern in _WARNINGS.items():
        if pattern.search(content):
            findings.append(_finding("warning", code, f"Signal found in {label}"))
    return findings


def audit_skill_catalog(catalog: SkillCatalogDocument) -> SkillAuditReport:
    audited: list[SkillAuditEntry] = []
    for entry in catalog.entries:
        findings: list[SkillAuditFinding] = []
        roots = {Path(location.path).resolve().parent for location in entry.locations}
        files: set[Path] = set()
        for root in roots:
            if root.is_dir():
                files.update(path for path in root.rglob("*") if path.is_file())
        scripts = sum(path.suffix.lower() in _SCRIPT_SUFFIXES for path in files)
        if not entry.description.strip():
            findings.append(_finding("warning", "missing-description", "Missing description"))
        if len(entry.description.strip()) < 24:
            findings.append(_finding("warning", "thin-description", "Description is too short"))
        if not files:
            findings.append(_finding("critical", "missing-content", "Skill files are unavailable"))
        if len(files) > _MAX_FILES:
            findings.append(
                _finding("warning", "large-bundle", f"Bundle contains {len(files)} files")
            )
        if scripts:
            findings.append(
                _finding("info", "contains-scripts", f"Bundle contains {scripts} script files")
            )
        scanned = 0
        for path in sorted(files):
            try:
                size = path.stat().st_size
                if scanned + size > _MAX_SCAN_BYTES:
                    findings.append(
                        _finding("warning", "scan-limit", "Static scan byte limit reached")
                    )
                    break
                content = path.read_text(encoding="utf-8", errors="ignore")
                scanned += size
            except OSError as exc:
                findings.append(_finding("warning", "unreadable-file", str(exc)))
                continue
            findings.extend(scan_skill_text(content, label=path.name))
        unique = {(item.severity, item.code, item.message): item for item in findings}
        findings = list(unique.values())
        score = 100
        score -= sum(35 for item in findings if item.severity == "critical")
        score -= sum(8 for item in findings if item.severity == "warning")
        score = max(0, score)
        disposition = "blocked" if any(item.severity == "critical" for item in findings) else (
            "review" if any(item.severity == "warning" for item in findings) else "candidate"
        )
        audited.append(
            SkillAuditEntry(
                entry_id=entry.id,
                name=entry.name,
                fingerprint=entry.fingerprint,
                reviewed=entry.reviewed,
                score=score,
                disposition=disposition,
                files=len(files),
                scripts=scripts,
                findings=findings,
            )
        )
    return SkillAuditReport(
        generated_at=datetime.now(UTC),
        catalog_generated_at=catalog.generated_at,
        entries=audited,
    )
