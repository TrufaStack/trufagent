from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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


def test_running_prepare_does_not_load_legacy_delegation_domain(tmp_path: Path) -> None:
    intake = tmp_path / "intake.json"
    intake.write_text('{"task":"Change one fixed label.","signal_overrides":{}}')
    script = (
        "import sys; from trufagent.cli import main; "
        f"code=main(['prepare',{str(intake)!r},{str(tmp_path)!r},'--project','demo']); "
        "raise SystemExit(code or int('trufagent.domain.delegation' in sys.modules))"
    )

    completed = subprocess.run([sys.executable, "-c", script], check=False)

    assert completed.returncode == 0
