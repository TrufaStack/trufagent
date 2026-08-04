from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_importing_stable_cli_does_not_load_delegation_runtime() -> None:
    modules = [
        "trufagent.experimental.attempt",
        "trufagent.experimental.attempt_fs",
        "trufagent.experimental.codex_shadow_runner",
        "trufagent.experimental.coordinator_gate",
        "trufagent.experimental.context_projection",
        "trufagent.experimental.delegation",
        "trufagent.experimental.delegation_domain",
        "trufagent.experimental.delegation_executor",
        "trufagent.experimental.exploration_gate",
        "trufagent.experimental.fake_phase_adapter",
        "trufagent.experimental.retry_gate",
        "trufagent.experimental.shadow_phase_adapter",
        "trufagent.experimental.task_continuation",
        "trufagent.experimental.task_preview",
        "trufagent.experimental.usage_fs",
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


def test_running_prepare_does_not_load_experimental_runtime(tmp_path: Path) -> None:
    intake = tmp_path / "intake.json"
    intake.write_text('{"task":"Change one fixed label.","signal_overrides":{}}')
    script = (
        "import sys; from trufagent.cli import main; "
        f"code=main(['prepare',{str(intake)!r},{str(tmp_path)!r},'--project','demo']); "
        "raise SystemExit(code or int(any(name.startswith('trufagent.experimental') "
        "for name in sys.modules)))"
    )

    completed = subprocess.run([sys.executable, "-c", script], check=False)

    assert completed.returncode == 0
