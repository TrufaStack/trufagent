from __future__ import annotations

import json
import secrets
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trufagent.application.errors import SafeAdapterError
from trufagent.application.promotion import ContextProjectionPolicy
from trufagent.domain.attempt import ProviderEventType
from trufagent.domain.delegation import (
    ActionScope,
    DelegationStep,
    PhaseHandoff,
    UsageRecord,
)
from trufagent.domain.task import Harness, ModelTier
from trufagent.infrastructure.context_projection import create_context_projection
from trufagent.infrastructure.shadow_phase_adapter import ShadowProgress, ShadowResult


class ShadowProviderError(SafeAdapterError):
    pass


class ShadowProcessError(ShadowProviderError):
    diagnostic_code = "process-exit"

    def __init__(self, code: str = "process-exit") -> None:
        super().__init__("Codex shadow process failed")
        self.diagnostic_code = code


class ShadowTimeoutError(ShadowProviderError):
    diagnostic_code = "provider-timeout"

    def __init__(
        self,
        *,
        usage: UsageRecord,
        progress: ShadowProgress | None = None,
    ) -> None:
        super().__init__("Codex shadow provider timed out")
        self.usage = usage
        self.progress = progress or ShadowProgress()


class ShadowResponseCode(StrEnum):
    JSONL_INVALID = "jsonl-invalid"
    USAGE_INVALID = "usage-invalid"
    MISSING_AGENT_MESSAGE = "missing-agent-message"
    HANDOFF_SCHEMA_INVALID = "handoff-schema-invalid"


class ShadowResponseError(ShadowProviderError):
    def __init__(
        self,
        code: ShadowResponseCode,
        *,
        usage: UsageRecord,
        progress: ShadowProgress | None = None,
    ) -> None:
        super().__init__("Codex shadow response rejected")
        self.diagnostic_code = code.value
        self.usage = usage
        self.progress = progress or ShadowProgress()


RunCommand = Callable[..., subprocess.CompletedProcess[str]]

_EFFORT = {
    ModelTier.ECONOMY: "low",
    ModelTier.BALANCED: "medium",
    ModelTier.FRONTIER: "high",
}

_TARGET_LIMIT = 24
_FILE_LIMIT = 12
_TIMEOUT_SECONDS = 180


def shadow_network_is_default_deny() -> bool:
    """Report the fixed delegate policy; user configuration cannot override it."""
    return True


class ShadowPreflight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.shadow-preflight\.v1$")
    status: str = "ready"
    summary: str
    next_actions: tuple[str, ...]
    artifacts: tuple[str, ...] = ()
    model: str
    tier: ModelTier
    budget_limit_usd: Decimal
    authorized_estimate_usd: Decimal
    target_count: int = Field(ge=0, le=_TARGET_LIMIT)
    target_limit: int = _TARGET_LIMIT
    file_limit: int = _FILE_LIMIT
    timeout_seconds: int = _TIMEOUT_SECONDS
    prompt_chars: int = Field(ge=1)
    memory_ids: tuple[str, ...] = ()
    graph_state: str | None = None
    graph_commit: str | None = None
    graphify_version: str | None = None
    read_only: bool = True
    session_active: bool | None = None
    preview_fresh: bool | None = None


class CodexShadowRunner:
    def __init__(
        self,
        *,
        project_root: Path,
        session_id: str,
        task: str,
        schema_path: Path,
        required_symbols: list[str] | tuple[str, ...] = (),
        structural_targets: list[str] | tuple[str, ...] = (),
        authorized_estimate_usd: Decimal | None = None,
        context_policy: ContextProjectionPolicy | None = None,
        run_command: RunCommand = subprocess.run,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.session_id = session_id
        self.task = task
        self.schema_path = Path(schema_path).resolve()
        self.required_symbols = tuple(dict.fromkeys(required_symbols))
        self.structural_targets = tuple(dict.fromkeys(structural_targets))[:_TARGET_LIMIT]
        self.authorized_estimate_usd = authorized_estimate_usd
        self.context_policy = context_policy
        self.run_command = run_command

    def preflight(
        self,
        step: DelegationStep,
        *,
        budget_limit_usd: Decimal,
        memory_ids: tuple[str, ...] = (),
        preview_id: str | None = None,
        graph_state: str | None = None,
        graph_commit: str | None = None,
        graphify_version: str | None = None,
        session_active: bool | None = None,
        preview_fresh: bool | None = None,
    ) -> ShadowPreflight:
        if step.model is None or step.action_scope != ActionScope.READ_ONLY:
            raise ValueError("shadow preflight requires a read-only invokable step")
        if self.authorized_estimate_usd is None:
            raise ValueError("shadow preflight requires an authorized estimate")
        return ShadowPreflight(
            schema="trufagent.shadow-preflight.v1",
            summary="Read-only shadow invocation is ready for explicit confirmation.",
            next_actions=("Review this preflight, then confirm the provider once.",),
            artifacts=(preview_id,) if preview_id else (),
            model=step.model,
            tier=step.tier,
            budget_limit_usd=budget_limit_usd,
            authorized_estimate_usd=self.authorized_estimate_usd,
            target_count=len(self.structural_targets),
            prompt_chars=len(self._prompt(step, ())),
            memory_ids=memory_ids,
            graph_state=graph_state,
            graph_commit=graph_commit,
            graphify_version=graphify_version,
            session_active=session_active,
            preview_fresh=preview_fresh,
        )

    def run(
        self,
        step: DelegationStep,
        previous: tuple[PhaseHandoff, ...],
    ) -> ShadowResult:
        if step.model is None or step.tier == ModelTier.NONE:
            raise ValueError("shadow runner requires an invokable model")
        started = time.monotonic()
        try:
            if self.context_policy is None:
                process = self._run_process(step, previous, self.project_root, self.schema_path)
            else:
                with tempfile.TemporaryDirectory(prefix="trufagent-context-") as temporary:
                    projection_root = Path(temporary) / "project"
                    create_context_projection(
                        self.project_root,
                        projection_root,
                        self.context_policy,
                    )
                    projected_schema = Path(temporary) / "handoff.schema.json"
                    shutil.copyfile(self.schema_path, projected_schema)
                    process = self._run_process(
                        step,
                        previous,
                        projection_root,
                        projected_schema,
                    )
        except subprocess.TimeoutExpired as exc:
            raise ShadowTimeoutError(
                usage=self._usage(step, {}),
                progress=self._timeout_progress(exc),
            ) from exc
        if process.returncode != 0:
            raise ShadowProcessError(self._classify_process_failure(process.stderr))
        usage = self._usage(step, {})
        progress = self._safe_progress(
            process.stdout,
            elapsed_ms=int((time.monotonic() - started) * 1_000),
        )
        try:
            events = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
            if any(not isinstance(event, dict) for event in events):
                raise TypeError("JSONL events must be objects")
        except (TypeError, json.JSONDecodeError) as exc:
            raise ShadowResponseError(
                ShadowResponseCode.JSONL_INVALID,
                usage=usage,
                progress=progress,
            ) from exc
        try:
            usage = self._usage_from_events(events, step)
        except (TypeError, ValueError, ValidationError) as exc:
            raise ShadowResponseError(
                ShadowResponseCode.USAGE_INVALID,
                usage=usage,
                progress=progress,
            ) from exc
        handoff = self._parse_handoff(events, usage=usage, progress=progress)
        return ShadowResult(
            handoff=handoff,
            usage=usage,
            progress=progress,
        )

    def _run_process(
        self,
        step: DelegationStep,
        previous: tuple[PhaseHandoff, ...],
        working_root: Path,
        schema_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_command(
            self._command(step, previous, working_root, schema_path),
            cwd=working_root,
            text=True,
            capture_output=True,
            timeout=_TIMEOUT_SECONDS,
        )

    def _command(
        self,
        step: DelegationStep,
        previous: tuple[PhaseHandoff, ...],
        working_root: Path,
        schema_path: Path,
    ) -> list[str]:
        prompt = self._prompt(step, previous)
        return [
            "codex",
            "--ignore-user-config",
            "--sandbox",
            "read-only",
            "--ask-for-approval",
            "never",
            "--cd",
            str(working_root),
            "--model",
            step.model or "",
            "--config",
            f'model_reasoning_effort="{_EFFORT[step.tier]}"',
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--output-schema",
            str(schema_path),
            "--json",
            prompt,
        ]

    @staticmethod
    def _classify_process_failure(stderr: str) -> str:
        lowered = stderr.lower()
        categories = (
            ("sandbox-unavailable", ("bwrap", "landlock", "sandbox")),
            ("model-unavailable", ("model not found", "unsupported model", "unknown model")),
            ("authentication-failed", ("not logged in", "unauthorized", "authentication")),
            ("schema-rejected", ("output schema", "json schema")),
        )
        for code, patterns in categories:
            if any(pattern in lowered for pattern in patterns):
                return code
        return "process-exit"

    def _prompt(
        self,
        step: DelegationStep,
        previous: tuple[PhaseHandoff, ...],
    ) -> str:
        compact_previous = [
            {
                "phase": item.phase.value,
                "status": item.status.value,
                "summary": item.summary,
                "evidence": list(item.evidence),
                "artifacts": list(item.artifacts),
            }
            for item in previous
        ]
        symbols = json.dumps(self.required_symbols)
        targets = json.dumps(self.structural_targets)
        return (
            "You are a Trufagent shadow delegate. Operate read-only. Do not edit, "
            "create, delete, or format files. Do not execute or implement the "
            "requested change; read-only repository inspection is allowed. "
            "Return only the required phase handoff JSON. Use status success when "
            "the investigation produced a supported conclusion, or warning when "
            "the cause remains ambiguous. Never use status error. Keep "
            "root_cause_hint, safe_retry, and stop_condition null.\n\n"
            "This is a bounded delegate task, not a new user session: do not read "
            "general session history unless it appears in the inspection targets. "
            "Begin with the supplied symbols and targets. Do not perform a "
            "repository-wide scan.\n"
            "Inspect at most 12 files and record every inspected path in "
            "inspected_files. If the conclusion cannot be supported within that "
            "scope, stop early and return status warning.\n"
            f"Phase: {step.phase.value}\n"
            f"Task: {self.task}\n"
            f"Required symbols: {symbols}\n"
            f"Inspection targets: {targets}\n"
            f"Previous compact handoffs: {json.dumps(compact_previous)}"
        )

    @staticmethod
    def _timeout_progress(exc: subprocess.TimeoutExpired) -> ShadowProgress:
        output = exc.output or ""
        return CodexShadowRunner._safe_progress(
            output,
            elapsed_ms=int(float(exc.timeout) * 1_000),
        )

    @staticmethod
    def _safe_progress(output: str | bytes, *, elapsed_ms: int) -> ShadowProgress:
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        events: list[dict] = []
        for line in output.splitlines():
            try:
                event = json.loads(line)
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(event, dict):
                events.append(event)
        raw_first = events[0].get("type") if events else None
        known = {
            "thread.started": ProviderEventType.THREAD_STARTED,
            "turn.started": ProviderEventType.TURN_STARTED,
            "item.completed": ProviderEventType.ITEM_COMPLETED,
            "turn.completed": ProviderEventType.TURN_COMPLETED,
        }
        first = known.get(raw_first, ProviderEventType.OTHER) if raw_first else None
        return ShadowProgress(
            elapsed_ms=elapsed_ms,
            event_count=len(events),
            first_event_type=first,
        )

    @classmethod
    def _parse_handoff(
        cls,
        events: list[dict],
        *,
        usage: UsageRecord,
        progress: ShadowProgress,
    ) -> PhaseHandoff:
        messages = [
            message
            for event in events
            if event.get("type") == "item.completed"
            for message in cls._agent_messages(event.get("item"))
        ]
        if not messages:
            raise ShadowResponseError(
                ShadowResponseCode.MISSING_AGENT_MESSAGE,
                usage=usage,
                progress=progress,
            )
        try:
            if isinstance(messages[-1], dict):
                return PhaseHandoff.model_validate(messages[-1])
            return PhaseHandoff.model_validate_json(messages[-1])
        except (TypeError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            raise ShadowResponseError(
                ShadowResponseCode.HANDOFF_SCHEMA_INVALID,
                usage=usage,
                progress=progress,
            ) from exc

    @staticmethod
    def _agent_messages(item) -> list[str | dict]:
        if not isinstance(item, dict) or item.get("type") != "agent_message":
            return []
        text = item.get("text")
        if isinstance(text, (str, dict)):
            return [text]
        content = item.get("content")
        if not isinstance(content, list):
            return []
        return [
            block["text"]
            for block in content
            if isinstance(block, dict)
            and block.get("type") in {"output_text", "text"}
            and isinstance(block.get("text"), (str, dict))
        ]

    def _usage_from_events(
        self,
        events: list[dict],
        step: DelegationStep,
    ) -> UsageRecord:
        completed = next(
            (event for event in reversed(events) if event.get("type") == "turn.completed"),
            {},
        )
        return self._usage(step, completed.get("usage", {}))

    def _usage(self, step: DelegationStep, raw_usage: dict) -> UsageRecord:
        return UsageRecord(
            schema="trufagent.usage.v1",
            invocation_id=f"inv_{secrets.token_hex(8)}",
            session_id=self.session_id,
            recorded_at=datetime.now(UTC),
            phase=step.phase,
            harness=Harness.CODEX,
            model=step.model,
            input_tokens=raw_usage.get("input_tokens", 0),
            cached_input_tokens=raw_usage.get("cached_input_tokens", 0),
            output_tokens=raw_usage.get("output_tokens", 0),
            authorized_estimate_usd=self.authorized_estimate_usd,
            cost_usd=raw_usage.get("cost_usd"),
        )
