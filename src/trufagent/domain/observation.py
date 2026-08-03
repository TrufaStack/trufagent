from __future__ import annotations

from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field


class OperationStatus(StrEnum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class OperationError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    root_cause_hint: str
    safe_retry: str | None = None
    stop_condition: str


PayloadT = TypeVar("PayloadT")


class Observation[PayloadT](BaseModel):
    """Deterministic result envelope shared by core operations."""

    model_config = ConfigDict(extra="forbid")

    status: OperationStatus
    summary: str = Field(min_length=1, max_length=240)
    next_actions: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    data: PayloadT | None = None
    error: OperationError | None = None
