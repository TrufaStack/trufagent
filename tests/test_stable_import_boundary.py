from __future__ import annotations

import json
import subprocess
import sys


def test_importing_stable_cli_does_not_load_delegation_runtime() -> None:
    modules = [
        "trufagent.application.delegation",
        "trufagent.application.delegation_executor",
        "trufagent.application.retry_gate",
        "trufagent.domain.attempt",
        "trufagent.infrastructure.attempt_fs",
        "trufagent.infrastructure.codex_shadow_runner",
        "trufagent.infrastructure.fake_phase_adapter",
        "trufagent.infrastructure.shadow_phase_adapter",
        "trufagent.infrastructure.usage_fs",
    ]
    script = (
        "import json, sys; import trufagent.cli; "
        f"print(json.dumps(sorted(set({modules!r}) & set(sys.modules))))"
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == []
