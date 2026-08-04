import json
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

from trufagent.domain.task import ModelTier
from trufagent.experimental.codex_shadow_runner import (
    CodexShadowRunner,
    ShadowProcessError,
    ShadowResponseCode,
    ShadowResponseError,
    ShadowTimeoutError,
    shadow_network_is_default_deny,
)
from trufagent.experimental.delegation_domain import (
    ActionScope,
    DelegationPhase,
    DelegationStep,
    HandoffStatus,
)
from trufagent.experimental.promotion import ContextProjectionPolicy


def _step() -> DelegationStep:
    return DelegationStep(
        phase=DelegationPhase.EXPLORATION,
        tier=ModelTier.BALANCED,
        model="gpt-5.6-terra",
        action_scope=ActionScope.READ_ONLY,
        max_attempts=1,
    )


def _stdout() -> str:
    handoff = {
        "phase": "exploration",
        "status": "success",
        "summary": "Found the relevant boundary.",
        "next_actions": [],
        "artifacts": [],
        "evidence": ["source-read"],
        "worktree_changed": False,
        "root_cause_hint": None,
        "safe_retry": None,
        "stop_condition": None,
    }
    return "\n".join(
        [
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": json.dumps(handoff)},
                }
            ),
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 120,
                        "cached_input_tokens": 80,
                        "output_tokens": 30,
                    },
                }
            ),
        ]
    )


def test_codex_shadow_command_is_read_only_and_parses_compact_result(
    tmp_path: Path,
) -> None:
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, _stdout(), "")

    runner = CodexShadowRunner(
        project_root=tmp_path,
        session_id="ses_example",
        task="Inspect the save boundary.",
        schema_path=tmp_path / "schema.json",
        run_command=fake_run,
    )

    result = runner.run(_step(), ())

    assert result.handoff.status == HandoffStatus.SUCCESS
    assert result.usage.input_tokens == 120
    command = observed["command"]
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert command[command.index("--ask-for-approval") + 1] == "never"
    assert "--ignore-user-config" in command
    assert "--search" not in command
    assert shadow_network_is_default_deny() is True
    assert "Inspect the save boundary." in command[-1]
    assert "Never use status error" in command[-1]
    assert observed["kwargs"]["timeout"] == 180


def test_codex_shadow_uses_sanitized_projection_when_policy_is_present(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "safe.py").write_text("SAFE = True\n")
    (project / ".env").write_text("DO_NOT_COPY=this\n")
    schema = tmp_path / "schema.json"
    schema.write_text("{}")
    observed = {}

    def fake_run(command, **kwargs):
        working_root = Path(kwargs["cwd"])
        observed["root_is_projection"] = working_root != project
        observed["safe"] = (working_root / "safe.py").read_text()
        observed["env_exists"] = (working_root / ".env").exists()
        observed["schema_exists"] = Path(command[command.index("--output-schema") + 1]).exists()
        return subprocess.CompletedProcess(command, 0, _stdout(), "")

    runner = CodexShadowRunner(
        project_root=project,
        session_id="ses_example",
        task="Inspect safely.",
        schema_path=schema,
        context_policy=ContextProjectionPolicy(excluded_globs=(".env*",)),
        run_command=fake_run,
    )

    runner.run(_step(), ())

    assert observed == {
        "root_is_projection": True,
        "safe": "SAFE = True\n",
        "env_exists": False,
        "schema_exists": True,
    }


def test_codex_shadow_prompt_uses_bounded_structural_context(tmp_path: Path) -> None:
    observed = {}

    def fake_run(command, **kwargs):
        del kwargs
        observed["prompt"] = command[-1]
        return subprocess.CompletedProcess(command, 0, _stdout(), "")

    targets = [f"target-{index}" for index in range(30)]
    runner = CodexShadowRunner(
        project_root=tmp_path,
        session_id="ses_example",
        task="Inspect the save boundary.",
        schema_path=tmp_path / "schema.json",
        required_symbols=["resolveChecklistJobType"],
        structural_targets=targets,
        run_command=fake_run,
    )

    runner.run(_step(), ())

    prompt = observed["prompt"]
    assert 'Required symbols: ["resolveChecklistJobType"]' in prompt
    assert "target-0" in prompt
    assert "target-23" in prompt
    assert "target-24" not in prompt
    assert "Do not perform a repository-wide scan" in prompt
    assert "do not read general session history" in prompt
    assert "Inspect at most 12 files" in prompt
    assert "return status warning" in prompt


def test_codex_shadow_error_does_not_expose_process_output(tmp_path: Path) -> None:
    def fake_run(command, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(
            command,
            1,
            "SECRET=do-not-leak",
            "provider internal detail",
        )

    runner = CodexShadowRunner(
        project_root=tmp_path,
        session_id="ses_example",
        task="Inspect.",
        schema_path=tmp_path / "schema.json",
        run_command=fake_run,
    )

    with pytest.raises(ShadowProcessError) as raised:
        runner.run(_step(), ())

    assert raised.value.diagnostic_code == "process-exit"
    assert "SECRET" not in str(raised.value)
    assert "provider internal" not in str(raised.value)


@pytest.mark.parametrize(
    ("stderr", "expected"),
    [
        ("bwrap: operation not permitted SECRET=hidden", "sandbox-unavailable"),
        ("unsupported model: private-name", "model-unavailable"),
        ("authentication required token=hidden", "authentication-failed"),
        ("invalid output schema at /private/path", "schema-rejected"),
    ],
)
def test_codex_shadow_classifies_process_failure_without_exposing_stderr(
    tmp_path: Path,
    stderr: str,
    expected: str,
) -> None:
    def fake_run(command, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(command, 1, "", stderr)

    runner = CodexShadowRunner(
        project_root=tmp_path,
        session_id="ses_example",
        task="Inspect safely.",
        schema_path=tmp_path / "schema.json",
        run_command=fake_run,
    )

    with pytest.raises(ShadowProcessError) as raised:
        runner.run(_step(), ())

    assert raised.value.diagnostic_code == expected
    assert stderr not in str(raised.value)


def test_codex_shadow_timeout_preserves_unknown_cost_usage(tmp_path: Path) -> None:
    def fake_run(command, **kwargs):
        output = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "secret-id"}),
                json.dumps({"type": "turn.started"}),
                "partial SECRET payload",
            ]
        )
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=output)

    runner = CodexShadowRunner(
        project_root=tmp_path,
        session_id="ses_example",
        task="Inspect.",
        schema_path=tmp_path / "schema.json",
        run_command=fake_run,
    )

    with pytest.raises(ShadowTimeoutError) as raised:
        runner.run(_step(), ())

    assert raised.value.diagnostic_code == "provider-timeout"
    assert raised.value.usage.session_id == "ses_example"
    assert raised.value.usage.cost_usd is None
    assert raised.value.progress.event_count == 2
    assert raised.value.progress.first_event_type == "thread-started"
    assert raised.value.progress.elapsed_ms == 180_000
    assert "SECRET" not in str(raised.value)


def test_invalid_provider_response_preserves_unknown_cost_usage(tmp_path: Path) -> None:
    stdout = json.dumps(
        {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 321,
                "cached_input_tokens": 123,
                "output_tokens": 45,
            },
        }
    )

    def fake_run(command, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(command, 0, stdout, "")

    runner = CodexShadowRunner(
        project_root=tmp_path,
        session_id="ses_example",
        task="Inspect.",
        schema_path=tmp_path / "schema.json",
        run_command=fake_run,
    )

    with pytest.raises(ShadowResponseError) as raised:
        runner.run(_step(), ())

    assert raised.value.diagnostic_code == ShadowResponseCode.MISSING_AGENT_MESSAGE
    assert raised.value.usage.input_tokens == 321
    assert raised.value.usage.output_tokens == 45
    assert raised.value.usage.cost_usd is None


def test_provider_reported_cost_remains_distinct_from_authorized_estimate(
    tmp_path: Path,
) -> None:
    lines = [json.loads(line) for line in _stdout().splitlines()]
    lines[-1]["usage"]["cost_usd"] = "0.03"

    def fake_run(command, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(
            command,
            0,
            "\n".join(json.dumps(line) for line in lines),
            "",
        )

    result = CodexShadowRunner(
        project_root=tmp_path,
        session_id="ses_example",
        task="Inspect.",
        schema_path=tmp_path / "schema.json",
        authorized_estimate_usd=Decimal("0.05"),
        run_command=fake_run,
    ).run(_step(), ())

    assert result.usage.authorized_estimate_usd == Decimal("0.05")
    assert result.usage.cost_usd == Decimal("0.03")


def test_content_block_agent_message_is_supported(tmp_path: Path) -> None:
    handoff = json.loads(json.loads(_stdout().splitlines()[0])["item"]["text"])
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "content": [{"type": "output_text", "text": handoff}],
                    },
                }
            ),
            _stdout().splitlines()[1],
        ]
    )

    def fake_run(command, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(command, 0, stdout, "")

    result = CodexShadowRunner(
        project_root=tmp_path,
        session_id="ses_example",
        task="Inspect.",
        schema_path=tmp_path / "schema.json",
        run_command=fake_run,
    ).run(_step(), ())

    assert result.handoff.status == HandoffStatus.SUCCESS


def test_warning_handoff_with_null_recovery_fields_is_supported(tmp_path: Path) -> None:
    handoff = {
        "phase": "exploration",
        "status": "warning",
        "summary": "Cause remains ambiguous.",
        "next_actions": ["Narrow the reproduction."],
        "artifacts": [],
        "evidence": ["read-only-inspection"],
        "worktree_changed": False,
        "root_cause_hint": None,
        "safe_retry": None,
        "stop_condition": None,
    }
    stdout = json.dumps(
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": json.dumps(handoff)},
        }
    )

    def fake_run(command, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(command, 0, stdout, "")

    result = CodexShadowRunner(
        project_root=tmp_path,
        session_id="ses_example",
        task="Inspect.",
        schema_path=tmp_path / "schema.json",
        run_command=fake_run,
    ).run(_step(), ())

    assert result.handoff.status == HandoffStatus.WARNING


@pytest.mark.parametrize(
    ("stdout", "expected_code"),
    [
        ("not-json", ShadowResponseCode.JSONL_INVALID),
        (
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "{}"},
                }
            ),
            ShadowResponseCode.HANDOFF_SCHEMA_INVALID,
        ),
    ],
)
def test_response_failures_have_closed_safe_codes(
    tmp_path: Path,
    stdout: str,
    expected_code: ShadowResponseCode,
) -> None:
    def fake_run(command, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(command, 0, stdout, "")

    runner = CodexShadowRunner(
        project_root=tmp_path,
        session_id="ses_example",
        task="Inspect.",
        schema_path=tmp_path / "schema.json",
        run_command=fake_run,
    )

    with pytest.raises(ShadowResponseError) as raised:
        runner.run(_step(), ())

    assert raised.value.diagnostic_code == expected_code
