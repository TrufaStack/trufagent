from pathlib import Path

import yaml


def test_graphify_first_benchmark_declares_multiple_targeted_surfaces() -> None:
    root = Path(__file__).parents[1]
    suite = yaml.safe_load((root / "evals" / "graphify-first.yaml").read_text())
    script = (root / "scripts" / "benchmark_graphify_first.py").read_text()

    assert len(suite["cases"]) == 7
    assert sum(case["expected_graph_queries"] for case in suite["cases"]) == 3
    assert {case["expected_disposition"] for case in suite["cases"]} == {
        "model-free",
        "shadow-required",
    }
    assert all("signals" in case for case in suite["cases"])
    assert "model_invocations" in script
    assert "evaluate_graphify_applicability" in script
    assert "evaluate_graphify_first" in script
