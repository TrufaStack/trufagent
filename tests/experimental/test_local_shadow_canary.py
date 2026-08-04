import json
import subprocess
import sys
from pathlib import Path


def test_local_shadow_canary_passes_every_deterministic_judge() -> None:
    root = Path(__file__).parents[2]
    process = subprocess.run(
        [sys.executable, str(root / "scripts" / "run_local_shadow_canary.py")],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    report = json.loads(process.stdout)

    assert process.returncode == 0
    assert report["status"] == "passed"
    assert report["provider_invocations"] == 0
    assert report["simulated_runner_calls"] == 1
    assert report["known_cost_usd"] == "0.02"
    assert all(report["judges"].values())
