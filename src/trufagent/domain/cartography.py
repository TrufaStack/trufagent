from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class GraphState(StrEnum):
    MISSING_TOOL = "missing_tool"
    MISSING_GRAPH = "missing_graph"
    BUILDING = "building"
    FRESH = "fresh"
    DIRTY_WORKTREE = "dirty_worktree"
    STALE_COMMIT = "stale_commit"
    INCOMPLETE = "incomplete"
    CORRUPT = "corrupt"
    VERSION_MISMATCH = "version_mismatch"
    ERROR = "error"


class GraphStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: GraphState
    project_root: str
    graph_path: str | None = None
    graphify_version: str | None = None
    built_at_commit: str | None = None
    head_commit: str | None = None
    source_fingerprint: str | None = None
    warnings: list[str] = Field(default_factory=list)


class GraphReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    label: str
    source_file: str | None = None
    confidence: str | None = None


class GraphQueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    nodes: list[GraphReference] = Field(default_factory=list)
    edges: list[str] = Field(default_factory=list)
    graphify_version: str
    graph_commit: str | None = None
    graph_state: GraphState | None = None
    truncated: bool = False
