"""Unit tests for ResultCollector — no browser required."""
from __future__ import annotations

import pytest

from src.core.enums import ActionType, FailurePhase, StepStatus
from src.workflow.execution_context import ExecutionContext
from src.workflow.result_collector import ResultCollector


def _ctx(**kwargs) -> ExecutionContext:
    defaults = dict(
        workflow_name="WF",
        tab_name="Tab1",
        page_name="Page1",
        section_name="Sec1",
        element_name="El1",
    )
    defaults.update(kwargs)
    return ExecutionContext(**defaults)


class TestResultCollector:
    def setup_method(self):
        self.collector = ResultCollector("TestWorkflow")

    def test_initial_summary_is_empty(self):
        summary = self.collector.summary()
        assert summary.total == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.skipped == 0

    def test_record_pass(self):
        ctx = _ctx()
        self.collector.record_pass(ctx, ActionType.CLICK, duration_ms=50.0)
        summary = self.collector.summary()
        assert summary.total == 1
        assert summary.passed == 1
        assert summary.failed == 0

    def test_record_fail(self):
        ctx = _ctx()
        self.collector.record_fail(
            ctx, ActionType.INPUT,
            error_message="Element not found",
            failure_phase=FailurePhase.ACTION,
        )
        summary = self.collector.summary()
        assert summary.total == 1
        assert summary.failed == 1
        assert summary.steps[0].status == StepStatus.FAILED
        assert summary.steps[0].failure_phase == FailurePhase.ACTION

    def test_record_skip(self):
        ctx = _ctx()
        self.collector.record_skip(ctx, ActionType.NOOP, reason="page load failed")
        summary = self.collector.summary()
        assert summary.skipped == 1
        assert summary.steps[0].error_message == "page load failed"

    def test_multiple_steps_aggregate_correctly(self):
        self.collector.record_pass(_ctx(element_name="A"), ActionType.CLICK)
        self.collector.record_pass(_ctx(element_name="B"), ActionType.INPUT)
        self.collector.record_fail(_ctx(element_name="C"), ActionType.CLICK, error_message="err")
        self.collector.record_skip(_ctx(element_name="D"), ActionType.NOOP)

        summary = self.collector.summary()
        assert summary.total == 4
        assert summary.passed == 2
        assert summary.failed == 1
        assert summary.skipped == 1

    def test_start_and_finish_sets_timestamps(self):
        self.collector.start()
        self.collector.finish()
        summary = self.collector.summary()
        assert summary.start_time is not None
        assert summary.end_time is not None
        assert summary.duration_seconds is not None
        assert summary.duration_seconds >= 0

    def test_passed_rate_all_pass(self):
        for i in range(4):
            self.collector.record_pass(_ctx(element_name=f"el{i}"), ActionType.CLICK)
        assert self.collector.summary().passed_rate == 100.0

    def test_passed_rate_zero_total(self):
        assert self.collector.summary().passed_rate == 0.0

    def test_step_result_location(self):
        ctx = _ctx(
            workflow_name="WF",
            tab_name="Tab",
            page_name="Page",
            section_name="Sec",
            element_name="El",
        )
        result = self.collector.record_pass(ctx, ActionType.CLICK)
        assert "WF" in result.location
        assert "Tab" in result.location
        assert "El" in result.location

    def test_screenshot_path_recorded(self):
        ctx = _ctx()
        result = self.collector.record_fail(
            ctx, ActionType.CLICK,
            error_message="timeout",
            screenshot_path="/tmp/screenshot.png",
        )
        assert result.screenshot_path == "/tmp/screenshot.png"


class TestExecutionContext:
    def test_at_tab(self):
        ctx = ExecutionContext(workflow_name="WF")
        child = ctx.at_tab("Tab1")
        assert child.tab_name == "Tab1"
        assert child.page_name == ""

    def test_at_page(self):
        ctx = ExecutionContext(workflow_name="WF", tab_name="Tab1")
        child = ctx.at_page("Page1")
        assert child.tab_name == "Tab1"
        assert child.page_name == "Page1"

    def test_at_section(self):
        ctx = ExecutionContext(workflow_name="WF", tab_name="T", page_name="P")
        child = ctx.at_section("Sec")
        assert child.section_name == "Sec"
        assert child.element_name == ""

    def test_str_representation(self):
        ctx = ExecutionContext(
            workflow_name="WF", tab_name="T", page_name="P",
            section_name="S", element_name="E"
        )
        s = str(ctx)
        assert "WF" in s
        assert "E" in s
        assert ">" in s
