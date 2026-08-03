from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml

from trufagent.application.exploration_gate import (
    ExplorationDisposition,
    evaluate_graphify_applicability,
    evaluate_graphify_first,
)
from trufagent.domain.task import TaskSignals
from trufagent.infrastructure.graphify_adapter import GraphifyAdapter


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--suite",
        type=Path,
        default=Path("evals/graphify-first.yaml"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    suite = yaml.safe_load(args.suite.read_text(encoding="utf-8"))
    results = []
    for case in suite["cases"]:
        started = time.monotonic()
        signals = TaskSignals.model_validate(case["signals"])
        applicability = evaluate_graphify_applicability(
            signals=signals,
            required_symbols=case["required_symbols"],
        )
        graph_queries = 0
        if not applicability.should_query:
            disposition = ExplorationDisposition.SHADOW_REQUIRED
            artifacts: list[str] = []
            reasons = list(applicability.reasons)
        else:
            graph = GraphifyAdapter().query(root, case["question"], token_budget=12_000)
            graph_queries = 1
            gate = evaluate_graphify_first(
                signals=signals,
                graph=graph,
                required_symbols=case["required_symbols"],
            )
            disposition = gate.disposition
            artifacts = list(gate.artifacts)
            reasons = list(gate.reasons)
        results.append(
            {
                "id": case["id"],
                "disposition": disposition.value,
                "expected_disposition": case["expected_disposition"],
                "graph_queries": graph_queries,
                "expected_graph_queries": case["expected_graph_queries"],
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "model_invocations": 0,
                "artifacts": artifacts,
                "reasons": reasons,
            }
        )
    passed = all(
        item["disposition"] == item["expected_disposition"]
        and item["graph_queries"] == item["expected_graph_queries"]
        for item in results
    )
    report = {
        "schema": suite["schema"],
        "passed": passed,
        "graph_queries": sum(item["graph_queries"] for item in results),
        "model_invocations": 0,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
