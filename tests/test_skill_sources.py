from __future__ import annotations

import hashlib
import io
import zipfile

from trufagent.infrastructure.skill_sources_github import PILOT_SOURCES, sync_pilot_sources


def test_remote_registry_pins_each_pilot_source_to_an_observed_commit() -> None:
    def fetch(url: str) -> dict:
        repository = next(name for name in PILOT_SOURCES if f"repos/{name}" in url)
        if "/commits/" in url:
            return {"sha": f"sha-{repository.replace('/', '-')}"}
        return {
            "full_name": repository,
            "html_url": f"https://github.com/{repository}",
            "default_branch": "main",
            "stargazers_count": 42,
            "forks_count": 7,
            "license": {"spdx_id": "MIT"},
            "pushed_at": "2026-08-01T00:00:00Z",
        }

    content = "---\nname: example\ndescription: Example skill\n---\n# Safe\n"
    fingerprint = hashlib.sha256(content.encode()).hexdigest()
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("repo/skills/example/SKILL.md", content)
        archive.writestr("repo/skills/example/check.py", "print('ok')\n")
    registry = sync_pilot_sources(
        {fingerprint}, fetch=fetch, fetch_archive=lambda _url: archive_buffer.getvalue()
    )

    assert len(registry.sources) == 4
    assert {source.repository for source in registry.sources} == set(PILOT_SOURCES)
    assert all(source.head_sha.startswith("sha-") for source in registry.sources)
    assert sum(source.trust == "official" for source in registry.sources) == 3
    assert all(source.skill_files == 1 for source in registry.sources)
    assert all(source.support_scripts == 1 for source in registry.sources)
    assert all(source.local_duplicates == 1 for source in registry.sources)
    assert all(source.skills[0].name == "example" for source in registry.sources)
