from __future__ import annotations

import hashlib
from pathlib import Path

from trufagent.domain.task import ModelTier
from trufagent.experimental.task_preview import FileTaskPreviewRepository
from trufagent.infrastructure.session_fs import FileSessionRepository


def continue_task(
    project_root: Path,
    preview_id: str,
    *,
    mode: str,
    task_text: str | None,
    confirm: bool,
) -> tuple[int, dict]:
    root = project_root.resolve()
    preview = FileTaskPreviewRepository(root).read(preview_id)
    current = FileSessionRepository(root).current()
    if current is None or current.id != preview.session_id:
        raise ValueError("task preview does not belong to the active session")
    if task_text is not None:
        observed = hashlib.sha256(task_text.encode()).hexdigest()
        if observed != preview.task_digest:
            raise ValueError("task text does not match the preview digest")
    if not confirm:
        return 2, {
            "schema": "trufagent.task-continuation.v1",
            "status": "confirmation-required",
            "preview_id": preview.preview_id,
            "mode": mode,
            "summary": preview.summary,
            "autonomy": preview.autonomy.value,
            "route": preview.route.model_dump(mode="json"),
            "next_action": "Review the preview, then rerun with --confirm.",
        }
    if preview.autonomy.value in {"confirm", "block"}:
        raise ValueError(
            f"preview autonomy {preview.autonomy.value} requires resolving its gate first"
        )
    if mode == "shadow":
        if task_text is None:
            raise ValueError("shadow continuation requires --task-text")
        if preview.route.exploration == ModelTier.NONE:
            return 0, {
                "schema": "trufagent.task-continuation.v1",
                "status": "not-needed",
                "preview_id": preview.preview_id,
                "mode": "shadow",
                "summary": "Model exploration is already tier none.",
                "next_action": "Use local continuation.",
            }
        return 0, {
            "schema": "trufagent.task-continuation.v1",
            "status": "authorization-required",
            "preview_id": preview.preview_id,
            "mode": "shadow",
            "signals": preview.signals.model_dump(mode="json"),
            "required_symbols": list(preview.required_symbols),
            "model_tier": preview.route.exploration.value,
            "required_inputs": [
                "verified_task_text",
                "budget_limit_usd",
                "estimated_cost_usd",
                "confirm_provider",
            ],
            "shadow_invocation": {
                "command": "trufagent delegation shadow",
                "project_root": str(root),
                "session": preview.session_id,
                "preview": preview.preview_id,
                "task_text": "reuse the exact verified --task-text input",
                "inherits": ["signals", "required_symbols", "model_tier"],
                "required_flags": [
                    "--budget-limit-usd",
                    "--estimated-cost-usd",
                    "--confirm-provider",
                ],
            },
            "next_action": (
                "Authorize a budgeted read-only shadow invocation; "
                "execution and verification remain disabled."
            ),
        }
    return 0, {
        "schema": "trufagent.local-handoff.v1",
        "status": "ready",
        "preview_id": preview.preview_id,
        "mode": "local",
        "summary": preview.summary,
        "skills": list(preview.skills),
        "memory": list(preview.memory_ids),
        "structural_targets": list(preview.structural_targets),
        "evidence_required": list(preview.evidence_required),
        "warnings": list(preview.warnings),
        "next_action": "The host may implement locally within this evidence contract.",
    }
