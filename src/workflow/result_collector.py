from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from src.core.enums import ActionType, FailurePhase, StepStatus
from src.core.logger import get_logger
from src.models.element_models import ExecutionSummary, StepResult
from src.workflow.execution_context import ExecutionContext

logger = get_logger("result_collector")


class ResultCollector:
    """Accumulates :class:`StepResult` records during workflow execution."""

    def __init__(self, workflow_name: str) -> None:
        self._workflow_name = workflow_name
        self._steps: List[StepResult] = []
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None

    def start(self) -> None:
        self._start_time = datetime.now()
        logger.info("Workflow '%s' execution started", self._workflow_name)

    def finish(self) -> None:
        self._end_time = datetime.now()
        summary = self.summary()
        logger.info(
            "Workflow '%s' finished — total=%d passed=%d failed=%d skipped=%d (%.1fs)",
            self._workflow_name,
            summary.total,
            summary.passed,
            summary.failed,
            summary.skipped,
            summary.duration_seconds or 0,
        )

    def record_pass(
        self,
        ctx: ExecutionContext,
        action: ActionType,
        duration_ms: Optional[float] = None,
    ) -> StepResult:
        result = StepResult(
            workflow_name=ctx.workflow_name,
            tab_name=ctx.tab_name,
            page_name=ctx.page_name,
            section_name=ctx.section_name,
            element_name=ctx.element_name,
            action=action,
            status=StepStatus.PASSED,
            duration_ms=duration_ms,
        )
        self._steps.append(result)
        logger.debug("PASS  %s", ctx)
        return result

    def record_fail(
        self,
        ctx: ExecutionContext,
        action: ActionType,
        error_message: str,
        failure_phase: Optional[FailurePhase] = None,
        screenshot_path: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> StepResult:
        result = StepResult(
            workflow_name=ctx.workflow_name,
            tab_name=ctx.tab_name,
            page_name=ctx.page_name,
            section_name=ctx.section_name,
            element_name=ctx.element_name,
            action=action,
            status=StepStatus.FAILED,
            error_message=error_message,
            failure_phase=failure_phase,
            screenshot_path=screenshot_path,
            duration_ms=duration_ms,
        )
        self._steps.append(result)
        logger.error("FAIL  %s | phase=%s | %s", ctx, failure_phase, error_message)
        return result

    def record_skip(
        self,
        ctx: ExecutionContext,
        action: ActionType,
        reason: str = "",
    ) -> StepResult:
        result = StepResult(
            workflow_name=ctx.workflow_name,
            tab_name=ctx.tab_name,
            page_name=ctx.page_name,
            section_name=ctx.section_name,
            element_name=ctx.element_name,
            action=action,
            status=StepStatus.SKIPPED,
            error_message=reason or None,
        )
        self._steps.append(result)
        logger.debug("SKIP  %s | %s", ctx, reason)
        return result

    def summary(self) -> ExecutionSummary:
        passed = sum(1 for s in self._steps if s.status == StepStatus.PASSED)
        failed = sum(1 for s in self._steps if s.status == StepStatus.FAILED)
        skipped = sum(1 for s in self._steps if s.status == StepStatus.SKIPPED)
        return ExecutionSummary(
            workflow_name=self._workflow_name,
            total=len(self._steps),
            passed=passed,
            failed=failed,
            skipped=skipped,
            start_time=self._start_time,
            end_time=self._end_time,
            steps=list(self._steps),
        )
