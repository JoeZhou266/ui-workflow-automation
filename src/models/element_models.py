from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.core.enums import ActionType, FailurePhase, StepStatus


class StepResult(BaseModel):
    """Records the outcome of a single element interaction step."""

    workflow_name: str
    tab_name: str
    page_name: str
    section_name: str
    element_name: str
    action: ActionType
    status: StepStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None
    failure_phase: Optional[FailurePhase] = None
    screenshot_path: Optional[str] = None

    @property
    def location(self) -> str:
        return (
            f"{self.workflow_name} > {self.tab_name} > "
            f"{self.page_name} > {self.section_name} > {self.element_name}"
        )


class ExecutionSummary(BaseModel):
    """Aggregate result for a complete workflow run."""

    workflow_name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    steps: list[StepResult] = Field(default_factory=list)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def passed_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total * 100
