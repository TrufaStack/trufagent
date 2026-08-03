from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

from trufagent.application.live_evaluation import (
    LiveExpectation,
    LiveResponse,
    judge_live_response,
)


def _prompt(agent: str, case_id: str, task: str) -> str:
    invocation = "/trufagent" if agent == "claude" else "$trufagent"
    return f"""This is a controlled adapter evaluation.

Explicitly invoke {invocation} to prepare the task below. Do not implement it,
modify repository files, or execute the requested diagnostic commands. Stop
after interpreting the Trufagent runtime result. Report only the requested JSON.

Task ID: {case_id}
Task: {task}
"""


def _git_state(root: Path) -> bytes:
    return subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def _claude_command(
    schema: dict[str, Any],
    prompt: str,
    *,
    model: str,
    effort: str,
    max_budget_usd: float,
) -> list[str]:
    return [
        "claude",
        "-p",
        "--model",
        model,
        "--effort",
        effort,
        "--max-budget-usd",
        str(max_budget_usd),
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema, separators=(",", ":")),
        "--permission-mode",
        "acceptEdits",
        "--allowedTools",
        "Bash,Read,Write",
        "--no-session-persistence",
        prompt,
    ]


def _codex_command(
    root: Path,
    schema_path: Path,
    prompt: str,
    *,
    model: str,
    effort: str,
) -> list[str]:
    return [
        "codex",
        "--sandbox",
        "workspace-write",
        "--ask-for-approval",
        "never",
        "--cd",
        str(root),
        "--model",
        model,
        "--config",
        f'model_reasoning_effort="{effort}"',
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--output-schema",
        str(schema_path),
        "--json",
        prompt,
    ]


def _parse_claude(stdout: str) -> tuple[dict[str, Any], dict[str, Any]]:
    envelope = json.loads(stdout)
    structured = envelope.get("structured_output")
    if structured is None:
        result = envelope["result"]
        structured = json.loads(result) if isinstance(result, str) else result
    metrics = {
        "cost_usd": envelope.get("total_cost_usd"),
        "duration_ms": envelope.get("duration_ms"),
        "usage": envelope.get("usage", {}),
        "model_usage": envelope.get("modelUsage", {}),
    }
    return structured, metrics


def _parse_codex(stdout: str) -> tuple[dict[str, Any], dict[str, Any]]:
    events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    messages = [
        event["item"]["text"]
        for event in events
        if event.get("type") == "item.completed"
        and event.get("item", {}).get("type") == "agent_message"
    ]
    if not messages:
        raise ValueError("Codex did not emit an agent_message")
    completed = next(
        (event for event in reversed(events) if event.get("type") == "turn.completed"),
        {},
    )
    return json.loads(messages[-1]), {"usage": completed.get("usage", {})}


def run_case(
    *,
    agent: str,
    case: dict[str, Any],
    root: Path,
    schema_path: Path,
    model: str,
    effort: str,
    max_budget_usd: float,
) -> dict[str, Any]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    prompt = _prompt(agent, case["id"], case["task"])
    command = (
        _claude_command(
            schema,
            prompt,
            model=model,
            effort=effort,
            max_budget_usd=max_budget_usd,
        )
        if agent == "claude"
        else _codex_command(
            root,
            schema_path,
            prompt,
            model=model,
            effort=effort,
        )
    )
    before = _git_state(root)
    started = time.monotonic()
    process = subprocess.run(
        command,
        cwd=root,
        text=True,
        capture_output=True,
        timeout=240,
    )
    elapsed = time.monotonic() - started
    after = _git_state(root)
    if process.returncode != 0:
        raise RuntimeError(
            f"{agent}/{case['id']} failed ({process.returncode}): "
            f"stdout={process.stdout[-2000:]} stderr={process.stderr[-2000:]}"
        )
    parsed, metrics = (
        _parse_claude(process.stdout) if agent == "claude" else _parse_codex(process.stdout)
    )
    response = LiveResponse.model_validate(parsed)
    expected = LiveExpectation.model_validate(case["expected"])
    judged = judge_live_response(response, expected)
    dimensions = dict(judged.dimensions)
    dimensions["repo_unchanged"] = before == after
    return {
        "agent": agent,
        "model": model,
        "effort": effort,
        "case_id": case["id"],
        "passed": all(dimensions.values()),
        "dimensions": dimensions,
        "response": response.model_dump(mode="json"),
        "elapsed_seconds": round(elapsed, 3),
        "metrics": metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=["claude", "codex"], required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--model")
    parser.add_argument("--effort", default="low")
    parser.add_argument("--max-budget-usd", type=float, default=0.15)
    args = parser.parse_args()

    root = args.root.resolve()
    live_root = root / "evals" / "live"
    suite = yaml.safe_load((live_root / "tasks.yaml").read_text(encoding="utf-8"))
    case = next((item for item in suite["cases"] if item["id"] == args.case), None)
    if case is None:
        parser.error(f"unknown case: {args.case}")
    model = args.model or ("sonnet" if args.agent == "claude" else "gpt-5.6-sol")
    result = run_case(
        agent=args.agent,
        case=case,
        root=root,
        schema_path=live_root / "response-schema.json",
        model=model,
        effort=args.effort,
        max_budget_usd=args.max_budget_usd,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
