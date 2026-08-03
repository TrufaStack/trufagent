from __future__ import annotations

import hashlib
import io
import json
import urllib.request
import zipfile
from datetime import UTC, datetime

import yaml

from trufagent.domain.skill_sources import (
    RemoteSkillCandidate,
    RemoteSkillFinding,
    RemoteSkillRegistry,
    RemoteSkillSource,
)
from trufagent.infrastructure.skill_audit import scan_skill_text

PILOT_SOURCES = {
    "anthropics/skills": ("official", "standard-reference"),
    "addyosmani/agent-skills": ("community-reviewed", "engineering-workflows"),
    "huggingface/skills": ("official", "machine-learning"),
    "MicrosoftDocs/Agent-Skills": ("official", "microsoft-azure"),
}
_MAX_ARCHIVE_BYTES = 100_000_000
_MAX_ARCHIVE_FILES = 20_000
_MAX_REMOTE_SKILL_BYTES = 2_000_000


def _metadata(content: str, path: str) -> tuple[str, str]:
    if not content.startswith("---") or content.count("---") < 2:
        return path.rsplit("/", 2)[-2], ""
    _, frontmatter, _ = content.split("---", 2)
    try:
        payload = yaml.safe_load(frontmatter)
    except yaml.YAMLError:
        payload = {}
    payload = payload if isinstance(payload, dict) else {}
    return str(payload.get("name") or path.rsplit("/", 2)[-2]), str(
        payload.get("description") or ""
    )


def _github_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "trufagent"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
        return json.load(response)


def _github_archive(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "trufagent"})
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
        return response.read()


def sync_pilot_sources(
    local_fingerprints: set[str] | None = None,
    *,
    fetch=_github_json,
    fetch_archive=_github_archive,
) -> RemoteSkillRegistry:
    observed_at = datetime.now(UTC)
    local_fingerprints = local_fingerprints or set()
    sources: list[RemoteSkillSource] = []
    for repository, (trust, purpose) in PILOT_SOURCES.items():
        metadata = fetch(f"https://api.github.com/repos/{repository}")
        branch = metadata["default_branch"]
        commit = fetch(f"https://api.github.com/repos/{repository}/commits/{branch}")
        head_sha = commit["sha"]
        archive_url = f"https://codeload.github.com/{repository}/zip/{head_sha}"
        archive_bytes = fetch_archive(archive_url)
        if len(archive_bytes) > _MAX_ARCHIVE_BYTES:
            raise ValueError(f"remote archive for {repository} exceeds size limit")
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
        members = [item for item in archive.infolist() if not item.is_dir()]
        if len(members) > _MAX_ARCHIVE_FILES:
            raise ValueError(f"remote archive for {repository} contains too many files")
        paths = [item.filename for item in members]
        skill_paths = [path for path in paths if path.endswith("SKILL.md")]
        script_paths = [
            path
            for path in paths
            if path.lower().endswith((".py", ".sh", ".bash", ".ps1", ".js", ".ts", ".rb"))
        ]
        duplicates = 0
        warning_signals = 0
        critical_signals = 0
        remote_findings: list[RemoteSkillFinding] = []
        candidates: list[RemoteSkillCandidate] = []
        for path in skill_paths:
            member = archive.getinfo(path)
            if member.file_size > _MAX_REMOTE_SKILL_BYTES:
                critical_signals += 1
                remote_findings.append(
                    RemoteSkillFinding(path=path, severity="critical", code="oversized-skill")
                )
                continue
            content = archive.read(path).decode("utf-8", errors="replace")
            fingerprint = hashlib.sha256(content.encode("utf-8")).hexdigest()
            local_duplicate = fingerprint in local_fingerprints
            duplicates += local_duplicate
            findings = scan_skill_text(content, label=path)
            warning_signals += sum(item.severity == "warning" for item in findings)
            critical_signals += sum(item.severity == "critical" for item in findings)
            remote_findings.extend(
                RemoteSkillFinding(path=path, severity=item.severity, code=item.code)
                for item in findings
                if item.severity != "info"
            )
            name, description = _metadata(content, path)
            candidates.append(
                RemoteSkillCandidate(
                    name=name,
                    description=description,
                    path=path,
                    fingerprint=fingerprint,
                    local_duplicate=local_duplicate,
                    findings=[
                        RemoteSkillFinding(path=path, severity=item.severity, code=item.code)
                        for item in findings
                        if item.severity != "info"
                    ],
                )
            )
        sources.append(
            RemoteSkillSource(
                repository=metadata["full_name"],
                url=metadata["html_url"],
                trust=trust,
                purpose=purpose,
                stars=metadata["stargazers_count"],
                forks=metadata["forks_count"],
                license=(metadata.get("license") or {}).get("spdx_id"),
                default_branch=branch,
                head_sha=head_sha,
                pushed_at=metadata["pushed_at"],
                observed_at=observed_at,
                skill_files=len(skill_paths),
                support_scripts=len(script_paths),
                local_duplicates=duplicates,
                warning_signals=warning_signals,
                critical_signals=critical_signals,
                findings=remote_findings,
                skills=candidates,
            )
        )
    return RemoteSkillRegistry(generated_at=observed_at, sources=sources)
