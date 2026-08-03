from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from trufagent.application.plan_task import PlanTaskRequest, PlanTaskService, TaskPlan
from trufagent.application.task_extractor import (
    TaskExtractionResult,
    TaskIntake,
    extract_task_signals,
)


class PrepareTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intake: TaskIntake
    project: str = Field(min_length=1)
    project_root: Path
    include_user_memory: bool = False
    memory_token_budget: int = Field(default=2_000, ge=64)
    cartography_token_budget: int = Field(default=1_000, ge=64)
    use_skills: list[str] = Field(default_factory=list)
    without_skills: list[str] = Field(default_factory=list)


class PreparedTask(BaseModel):
    extraction: TaskExtractionResult
    plan: TaskPlan | None = None


class PrepareTaskService:
    def __init__(self, planner: PlanTaskService) -> None:
        self.planner = planner

    def prepare(self, request: PrepareTaskRequest) -> PreparedTask:
        extraction = extract_task_signals(request.intake)
        if not extraction.ready_to_plan:
            return PreparedTask(extraction=extraction)
        plan = self.planner.plan(
            PlanTaskRequest(
                task=request.intake.task,
                project=request.project,
                project_root=request.project_root,
                signals=extraction.signals,
                include_user_memory=request.include_user_memory,
                memory_token_budget=request.memory_token_budget,
                cartography_token_budget=request.cartography_token_budget,
                use_skills=request.use_skills,
                without_skills=request.without_skills,
                required_symbols=request.intake.required_symbols,
            )
        )
        return PreparedTask(extraction=extraction, plan=plan)
