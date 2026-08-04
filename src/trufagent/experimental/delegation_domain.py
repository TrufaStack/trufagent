from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trufagent.domain.task import Harness, ModelTier


class DelegationPhase(StrEnum):
    COORDINATOR = "coordinator"
    EXPLORATION = "exploration"
    EXECUTION = "execution"
    VERIFICATION = "verification"


class ActionScope(StrEnum):
    NONE = "none"
    READ_ONLY = "read-only"
    WORKTREE_WRITE = "worktree-write"


class HandoffStatus(StrEnum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class DelegationStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    phase: DelegationPhase
    tier: ModelTier
    model: str | None
    action_scope: ActionScope
    max_attempts: int = Field(ge=0, le=1)
    required_evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def skipped_phase_has_no_invocation(self) -> DelegationStep:
        skipped = self.tier == ModelTier.NONE
        if skipped != (self.model is None):
            raise ValueError("none tier and absent model must appear together")
        if skipped != (self.action_scope == ActionScope.NONE):
            raise ValueError("skipped phases must use action_scope none")
        if skipped != (self.max_attempts == 0):
            raise ValueError("skipped phases must have zero attempts")
        if self.phase != DelegationPhase.EXECUTION and (
            self.action_scope == ActionScope.WORKTREE_WRITE
        ):
            raise ValueError("only execution may write to the worktree")
        return self


class DelegationProtocol(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.delegation\.v1$")
    session_id: str
    harness: Harness
    budget_limit_usd: Decimal | None = Field(default=None, ge=0)
    max_parallel: int = Field(default=1, ge=1, le=1)
    steps: tuple[DelegationStep, ...]

    @model_validator(mode="after")
    def phases_are_unique_and_ordered(self) -> DelegationProtocol:
        phases = tuple(step.phase for step in self.steps)
        expected = tuple(DelegationPhase)
        if phases != expected:
            raise ValueError("delegation phases must be unique and ordered")
        return self


class PhaseHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    phase: DelegationPhase
    status: HandoffStatus
    summary: str = Field(min_length=1)
    next_actions: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    inspected_files: tuple[str, ...] = Field(default=(), max_length=12)
    worktree_changed: bool = False
    root_cause_hint: str | None = None
    safe_retry: str | None = None
    stop_condition: str | None = None

    @model_validator(mode="after")
    def errors_have_recovery_contract(self) -> PhaseHandoff:
        recovery = (self.root_cause_hint, self.safe_retry, self.stop_condition)
        if self.status == HandoffStatus.ERROR and not all(recovery):
            raise ValueError(
                "error recovery requires root_cause_hint, safe_retry, and stop_condition"
            )
        if self.status != HandoffStatus.ERROR and any(recovery):
            raise ValueError("recovery fields are reserved for error handoffs")
        return self


class DelegationRunReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: HandoffStatus
    summary: str = Field(min_length=1)
    next_actions: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    handoffs: tuple[PhaseHandoff, ...] = ()
    stopped_at: DelegationPhase | None = None


class UsageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: str = Field(alias="schema", pattern=r"^trufagent\.usage\.v1$")
    invocation_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    recorded_at: datetime
    phase: DelegationPhase
    harness: Harness
    model: str = Field(min_length=1)
    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    authorized_estimate_usd: Decimal | None = Field(default=None, ge=0)
    cost_usd: Decimal | None = Field(default=None, ge=0)


class UsageLedger(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    budget_limit_usd: Decimal | None = Field(default=None, ge=0)
    records: tuple[UsageRecord, ...] = ()

    @property
    def known_cost_usd(self) -> Decimal:
        return sum(
            (record.cost_usd for record in self.records if record.cost_usd is not None),
            start=Decimal("0"),
        )

    @property
    def has_unknown_cost(self) -> bool:
        return any(record.cost_usd is None for record in self.records)

    @property
    def has_unbounded_unknown_cost(self) -> bool:
        return any(
            record.cost_usd is None and record.authorized_estimate_usd is None
            for record in self.records
        )

    @property
    def reserved_cost_usd(self) -> Decimal:
        return sum(
            (
                record.cost_usd
                if record.cost_usd is not None
                else record.authorized_estimate_usd or Decimal("0")
                for record in self.records
            ),
            start=Decimal("0"),
        )

    @property
    def cost_status(self) -> str:
        if not self.records:
            return "empty"
        if self.has_unbounded_unknown_cost:
            return "unknown"
        if self.has_unknown_cost:
            return "estimated"
        return "actual"

    @property
    def remaining_budget_usd(self) -> Decimal | None:
        if self.budget_limit_usd is None:
            return None
        return self.budget_limit_usd - self.reserved_cost_usd

    def authorize(self, estimated_cost_usd: Decimal) -> None:
        if estimated_cost_usd < 0:
            raise ValueError("estimated cost cannot be negative")
        if (
            self.budget_limit_usd is not None
            and self.reserved_cost_usd + estimated_cost_usd > self.budget_limit_usd
        ):
            raise ValueError("estimated invocation would exceed session budget")

    def add(self, record: UsageRecord) -> UsageLedger:
        if record.session_id != self.session_id:
            raise ValueError("usage record belongs to a different session")
        if any(item.invocation_id == record.invocation_id for item in self.records):
            raise ValueError(f"duplicate invocation id: {record.invocation_id}")
        return self.model_copy(update={"records": (*self.records, record)})
