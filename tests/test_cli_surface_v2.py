from __future__ import annotations

import argparse

from trufagent.cli import _build_parser


def _choices(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    action = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return action.choices


def test_stable_cli_excludes_historical_and_global_management_commands() -> None:
    parser = _build_parser()
    commands = _choices(parser)

    assert {"task", "task-continue", "delegation", "promotion"}.isdisjoint(commands)
    assert {
        "prepare",
        "close",
        "memory",
        "graph",
        "cartography",
        "models",
        "skills",
        "init",
    } <= set(commands)
    assert set(_choices(commands["skills"])) == {"list", "search"}
    help_text = parser.format_help()
    assert "delegation" not in help_text
    assert "promotion" not in help_text
    assert "task-continue" not in help_text


def test_experimental_cli_preserves_historical_commands() -> None:
    commands = _choices(_build_parser(include_experimental=True))

    assert {"task", "task-continue", "delegation", "promotion"} <= set(commands)
    assert {"sync", "review", "audit", "sources", "sanitize", "import", "profile"} <= set(
        _choices(commands["skills"])
    )
