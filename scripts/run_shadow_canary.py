from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from trufagent.domain.task import (
    Harness,
    ModelRouting,
    ModelTier,
    TaskKind,
    TaskSignals,
)
from trufagent.experimental.codex_shadow_runner import CodexShadowRunner
from trufagent.experimental.delegation import compile_delegation_protocol
from trufagent.experimental.delegation_domain import HandoffStatus
from trufagent.experimental.delegation_executor import execute_dry_run
from trufagent.experimental.exploration_gate import (
    ExplorationDisposition,
    evaluate_graphify_applicability,
    evaluate_graphify_first,
)
from trufagent.experimental.shadow_phase_adapter import ShadowPhaseAdapter
from trufagent.experimental.usage_fs import JsonlUsageRepository
from trufagent.infrastructure.graphify_adapter import GraphifyAdapter


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--session", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument(
        "--signals",
        type=Path,
        help="Typed TaskSignals JSON; defaults to a known localized small change",
    )
    parser.add_argument("--model", default="gpt-5.6-terra")
    parser.add_argument("--required-symbol", action="append", default=[])
    parser.add_argument("--allow-shadow", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    started = time.monotonic()
    signals = (
        TaskSignals.model_validate_json(args.signals.read_text(encoding="utf-8"))
        if args.signals
        else TaskSignals(
            kind=TaskKind.SMALL_CHANGE,
            solution_known=True,
            localized=True,
        )
    )
    applicability = evaluate_graphify_applicability(
        signals=signals,
        required_symbols=args.required_symbol,
    )
    graph_queries = 0
    if applicability.should_query:
        graph = GraphifyAdapter().query(root, args.task, token_budget=12_000)
        graph_queries = 1
        gate = evaluate_graphify_first(
            signals=signals,
            graph=graph,
            required_symbols=args.required_symbol,
        )
    else:
        gate = None

    if gate is not None and gate.disposition == ExplorationDisposition.MODEL_FREE:
        result = {
            **gate.model_dump(mode="json"),
            "graph_queries": graph_queries,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "model_invocations": 0,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result))
        return 0
    if not args.allow_shadow:
        gate_payload = (
            gate.model_dump(mode="json")
            if gate is not None
            else {
                "status": "warning",
                "summary": "Graphify abstained before query; supervised shadow is required.",
                "next_actions": ["Rerun with --allow-shadow only after reviewing the reasons."],
                "artifacts": [],
                "disposition": ExplorationDisposition.SHADOW_REQUIRED.value,
                "handoff": None,
                "reasons": list(applicability.reasons),
            }
        )
        result = {
            **gate_payload,
            "graph_queries": graph_queries,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "model_invocations": 0,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result))
        return 1

    protocol = compile_delegation_protocol(
        session_id=args.session,
        project_root=root,
        harness=Harness.CODEX,
        route=ModelRouting(
            coordinator=ModelTier.NONE,
            exploration=ModelTier.BALANCED,
            execution=ModelTier.NONE,
            verification=ModelTier.NONE,
        ),
        evidence_required=[],
    )
    exploration = protocol.steps[1].model_copy(update={"model": args.model})
    protocol = protocol.model_copy(
        update={
            "steps": (
                protocol.steps[0],
                exploration,
                protocol.steps[2],
                protocol.steps[3],
            )
        }
    )
    runner = CodexShadowRunner(
        project_root=root,
        session_id=args.session,
        task=args.task,
        schema_path=root / "evals" / "shadow" / "handoff-schema.json",
    )
    adapter = ShadowPhaseAdapter(
        project_root=root,
        session_id=args.session,
        harness=Harness.CODEX,
        runner=runner,
        usage=JsonlUsageRepository(root),
    )
    report = execute_dry_run(protocol, adapter)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report.model_dump(mode="json")))
    return int(report.status != HandoffStatus.SUCCESS)


if __name__ == "__main__":
    raise SystemExit(main())
