from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from trufagent.application.errors import CartographyUnavailableError
from trufagent.domain.cartography import (
    GraphQueryResult,
    GraphReference,
    GraphState,
    GraphStatus,
)
from trufagent.infrastructure.worktree_fingerprint import fingerprint_worktree


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class GraphifyAdapterError(CartographyUnavailableError):
    pass


class GraphifyCommandError(GraphifyAdapterError):
    pass


CommandRunner = Callable[..., CommandResult]
VersionProvider = Callable[[], str]

_NODE_LINE = re.compile(
    r"^NODE (?P<label>.*?) \[src=(?P<source>.*?) loc=(?P<location>.*?) community=.*\]$"
)


def _default_runner(command: list[str], *, cwd: Path, timeout: int) -> CommandResult:
    completed = subprocess.run(  # noqa: S603 - fixed executable, argv only, no shell
        command,
        cwd=cwd,
        timeout=timeout,
        check=False,
        capture_output=True,
        text=True,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _installed_version() -> str:
    return version("graphifyy")


class GraphifyAdapter:
    """CLI adapter that keeps Graphify's derived data outside memory authority."""

    def __init__(
        self,
        *,
        command: list[str] | None = None,
        runner: CommandRunner = _default_runner,
        version_provider: VersionProvider = _installed_version,
        timeout: int = 120,
    ) -> None:
        self.command = command or [sys.executable, "-m", "graphify"]
        self.runner = runner
        self.version_provider = version_provider
        self.timeout = timeout

    def _version(self) -> str | None:
        try:
            return self.version_provider()
        except PackageNotFoundError:
            return None

    @staticmethod
    def _root(project_root: Path) -> Path:
        root = Path(project_root).resolve()
        if not root.is_dir():
            raise GraphifyAdapterError(f"project root is not a directory: {root}")
        return root

    @staticmethod
    def _graph_path(root: Path) -> Path:
        return root / "graphify-out" / "graph.json"

    def _run(self, arguments: list[str], *, root: Path) -> CommandResult:
        result = self.runner(self.command + arguments, cwd=root, timeout=self.timeout)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown Graphify failure"
            raise GraphifyCommandError(detail)
        return result

    def _git(self, root: Path, *arguments: str) -> str | None:
        result = self.runner(["git", *arguments], cwd=root, timeout=15)
        return result.stdout.strip() if result.returncode == 0 else None

    def status(self, project_root: Path) -> GraphStatus:
        root = self._root(project_root)
        graph_path = self._graph_path(root)
        graphify_version = self._version()
        if graphify_version is None:
            return GraphStatus(state=GraphState.MISSING_TOOL, project_root=str(root))
        if not graph_path.is_file():
            return GraphStatus(
                state=GraphState.MISSING_GRAPH,
                project_root=str(root),
                graph_path=str(graph_path),
                graphify_version=graphify_version,
            )

        try:
            payload = json.loads(graph_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return GraphStatus(
                state=GraphState.CORRUPT,
                project_root=str(root),
                graph_path=str(graph_path),
                graphify_version=graphify_version,
                warnings=[f"cannot parse graph.json: {exc}"],
            )
        if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), list):
            return GraphStatus(
                state=GraphState.CORRUPT,
                project_root=str(root),
                graph_path=str(graph_path),
                graphify_version=graphify_version,
                warnings=["graph.json does not contain a nodes list"],
            )

        built_at_commit = payload.get("built_at_commit")
        head_commit = self._git(root, "rev-parse", "HEAD")
        manifest_path = root / ".trufagent" / "cartography" / "manifest.json"
        source_fingerprint = None
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                source_fingerprint = manifest.get("source_fingerprint")
            except (OSError, json.JSONDecodeError):
                source_fingerprint = None
        base = {
            "project_root": str(root),
            "graph_path": str(graph_path),
            "graphify_version": graphify_version,
            "built_at_commit": built_at_commit,
            "head_commit": head_commit,
            "source_fingerprint": source_fingerprint,
        }
        if not payload["nodes"]:
            return GraphStatus(state=GraphState.INCOMPLETE, **base)
        if built_at_commit and head_commit and built_at_commit != head_commit:
            return GraphStatus(state=GraphState.STALE_COMMIT, **base)
        dirty = self._git(root, "status", "--porcelain")
        if dirty:
            if source_fingerprint is not None and source_fingerprint == fingerprint_worktree(root):
                return GraphStatus(
                    state=GraphState.FRESH,
                    warnings=["fresh snapshot of a dirty worktree"],
                    **base,
                )
            return GraphStatus(state=GraphState.DIRTY_WORKTREE, **base)
        return GraphStatus(state=GraphState.FRESH, **base)

    def update(self, project_root: Path) -> GraphStatus:
        root = self._root(project_root)
        self._run(["update", str(root)], root=root)
        manifest_path = root / ".trufagent" / "cartography" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        provisional = self.status(root)
        manifest_path.write_text(
            json.dumps(
                {
                    "schema": "trufagent.cartography.v1",
                    "graphify_version": provisional.graphify_version,
                    "graph_path": provisional.graph_path,
                    "built_at_commit": provisional.built_at_commit,
                    "source_fingerprint": fingerprint_worktree(root),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return self.status(root)

    @staticmethod
    def _parse_result(output: str, status: GraphStatus) -> GraphQueryResult:
        nodes: list[GraphReference] = []
        edges: list[str] = []
        for line in output.splitlines():
            match = _NODE_LINE.match(line)
            if match:
                nodes.append(
                    GraphReference(
                        node_id=match.group("label"),
                        label=match.group("label"),
                        source_file=match.group("source") or None,
                    )
                )
            elif line.startswith("EDGE "):
                edges.append(line.removeprefix("EDGE "))
        return GraphQueryResult(
            summary=output.strip(),
            nodes=nodes,
            edges=edges,
            graphify_version=status.graphify_version or "unknown",
            graph_commit=status.built_at_commit,
            graph_state=status.state,
            truncated="[!] TRUNCATED" in output,
        )

    def query(
        self,
        project_root: Path,
        question: str,
        *,
        token_budget: int = 2_000,
    ) -> GraphQueryResult:
        root = self._root(project_root)
        status = self.status(root)
        if status.state in {
            GraphState.MISSING_TOOL,
            GraphState.MISSING_GRAPH,
            GraphState.CORRUPT,
            GraphState.INCOMPLETE,
        }:
            raise GraphifyAdapterError(f"graph is not queryable: {status.state.value}")
        graph_path = self._graph_path(root)
        result = self._run(
            [
                "query",
                question,
                "--budget",
                str(token_budget),
                "--graph",
                str(graph_path),
            ],
            root=root,
        )
        return self._parse_result(result.stdout, status)

    def affected(
        self,
        project_root: Path,
        label: str,
        *,
        relations: list[str],
        depth: int = 2,
    ) -> GraphQueryResult:
        root = self._root(project_root)
        status = self.status(root)
        if status.state in {
            GraphState.MISSING_TOOL,
            GraphState.MISSING_GRAPH,
            GraphState.CORRUPT,
            GraphState.INCOMPLETE,
        }:
            raise GraphifyAdapterError(f"graph is not queryable: {status.state.value}")
        arguments = ["affected", label]
        for relation in relations:
            arguments.extend(["--relation", relation])
        arguments.extend(["--depth", str(depth), "--graph", str(self._graph_path(root))])
        result = self._run(arguments, root=root)
        return self._parse_result(result.stdout, status)
