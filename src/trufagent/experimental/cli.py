from __future__ import annotations

from trufagent.cli import main as stable_main


def main(argv: list[str] | None = None) -> int:
    """Run the compatibility CLI with explicitly experimental commands enabled."""

    return stable_main(
        argv,
        include_experimental=True,
        prog="trufagent-experimental",
    )
