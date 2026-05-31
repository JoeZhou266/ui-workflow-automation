"""Unit tests for html_report utility functions.

Covers: HTML-01 through HTML-09
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Module-level factories (no imports at module level from src — tests import inline)
# ---------------------------------------------------------------------------

def _make_step(status="passed", **kwargs):
    """Build a StepResult for testing. Imports src inline to catch import errors."""
    from src.core.enums import ActionType, FailurePhase, StepStatus
    from src.models.element_models import StepResult

    status_enum = StepStatus(status)
    defaults = dict(
        workflow_name="WF",
        tab_name="Tab1",
        page_name="Page1",
        section_name="Sec1",
        element_name="El1",
        action=ActionType.CLICK,
        status=status_enum,
        duration_ms=42.0,
        error_message=None,
        failure_phase=None,
        screenshot_path=None,
    )
    defaults.update(kwargs)
    return StepResult(**defaults)


def _make_summary(steps=None):
    from src.core.enums import StepStatus
    from src.models.element_models import ExecutionSummary

    steps = steps or []
    return ExecutionSummary(
        workflow_name="WF",
        total=len(steps),
        passed=sum(1 for s in steps if s.status == StepStatus.PASSED),
        failed=sum(1 for s in steps if s.status == StepStatus.FAILED),
        skipped=sum(1 for s in steps if s.status == StepStatus.SKIPPED),
        steps=steps,
    )


# ---------------------------------------------------------------------------
# HTML-01: build_step_table returns valid HTML with all step rows
# ---------------------------------------------------------------------------

class TestBuildStepTable:
    def test_returns_details_block(self):
        from src.utils.html_report import build_step_table
        step = _make_step()
        summary = _make_summary([step])
        html = build_step_table(summary)
        assert "<details>" in html
        assert "</details>" in html

    def test_returns_summary_element(self):
        from src.utils.html_report import build_step_table
        step = _make_step()
        summary = _make_summary([step])
        html = build_step_table(summary)
        assert "<summary>" in html

    def test_contains_workflow_name(self):
        from src.utils.html_report import build_step_table
        step = _make_step()
        summary = _make_summary([step])
        html = build_step_table(summary)
        assert "WF" in html

    def test_contains_step_element_name(self):
        from src.utils.html_report import build_step_table
        step = _make_step(element_name="MyButton")
        summary = _make_summary([step])
        html = build_step_table(summary)
        assert "MyButton" in html

    def test_contains_step_count_in_summary(self):
        from src.utils.html_report import build_step_table
        steps = [_make_step(), _make_step(status="failed", error_message="boom", failure_phase="interaction")]
        summary = _make_summary(steps)
        html = build_step_table(summary)
        assert "2 steps" in html

    def test_empty_summary_returns_details_block(self):
        from src.utils.html_report import build_step_table
        summary = _make_summary([])
        html = build_step_table(summary)
        assert "<details>" in html
        assert "0 steps" in html


# ---------------------------------------------------------------------------
# HTML-02: PASSED rows — green background
# ---------------------------------------------------------------------------

class TestPassedStepRowColor:
    def test_passed_row_has_green_background(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(status="passed")
        html = _step_row_html(step)
        assert "#d4edda" in html


# ---------------------------------------------------------------------------
# HTML-03: FAILED rows — red background + error_message + failure_phase
# ---------------------------------------------------------------------------

class TestFailedStepRow:
    def test_failed_row_has_red_background(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(status="failed", error_message="timeout", failure_phase="interaction")
        html = _step_row_html(step)
        assert "#f8d7da" in html

    def test_failed_row_contains_error_message(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(status="failed", error_message="Element not found", failure_phase="interaction")
        html = _step_row_html(step)
        assert "Element not found" in html

    def test_failed_row_contains_failure_phase(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(status="failed", error_message="err", failure_phase="interaction")
        html = _step_row_html(step)
        assert "interaction" in html

    def test_passed_row_has_no_error_content(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(status="passed")
        html = _step_row_html(step)
        # PASSED rows should not have failure_phase text in their error cell
        assert "phase:" not in html


# ---------------------------------------------------------------------------
# HTML-04: SKIPPED rows — yellow background
# ---------------------------------------------------------------------------

class TestSkippedStepRow:
    def test_skipped_row_has_yellow_background(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(status="skipped")
        html = _step_row_html(step)
        assert "#fff3cd" in html


# ---------------------------------------------------------------------------
# HTML-05: Screenshot link rendered as <a><img></a> when screenshot_path set
# ---------------------------------------------------------------------------

class TestScreenshotLink:
    def test_screenshot_renders_img_tag(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(screenshot_path="reports/screenshots/20260530_foo.png")
        html = _step_row_html(step)
        assert "<img" in html

    def test_screenshot_renders_anchor_tag(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(screenshot_path="reports/screenshots/20260530_foo.png")
        html = _step_row_html(step)
        assert "<a href=" in html

    def test_screenshot_link_uses_relative_path(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(screenshot_path="reports/screenshots/20260530_foo.png")
        html = _step_row_html(step, reports_dir="reports")
        assert "screenshots/20260530_foo.png" in html

    def test_screenshot_img_has_max_width(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(screenshot_path="reports/screenshots/20260530_foo.png")
        html = _step_row_html(step)
        assert "max-width:200px" in html


# ---------------------------------------------------------------------------
# HTML-06: No screenshot when screenshot_path is None
# ---------------------------------------------------------------------------

class TestNoScreenshot:
    def test_no_img_when_screenshot_path_none(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(screenshot_path=None)
        html = _step_row_html(step)
        assert "<img" not in html

    def test_no_anchor_when_screenshot_path_none(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(screenshot_path=None)
        html = _step_row_html(step)
        assert "<a href=" not in html


# ---------------------------------------------------------------------------
# HTML-07: _relative_path returns correct relative path within reports_dir
# ---------------------------------------------------------------------------

class TestRelativePath:
    def test_relative_path_within_reports(self):
        from src.utils.html_report import _relative_path
        result = _relative_path("reports/screenshots/20260530_foo.png", "reports")
        assert result == "screenshots/20260530_foo.png"

    def test_relative_path_nested(self):
        from src.utils.html_report import _relative_path
        result = _relative_path("reports/videos/20260530_test.mp4", "reports")
        assert result == "videos/20260530_test.mp4"


# ---------------------------------------------------------------------------
# HTML-08: _relative_path returns None when path not under reports_dir
# ---------------------------------------------------------------------------

class TestRelativePathOutside:
    def test_returns_none_for_path_outside_reports(self):
        from src.utils.html_report import _relative_path
        result = _relative_path("/tmp/outside/foo.png", "reports")
        assert result is None

    def test_returns_none_for_unrelated_path(self):
        from src.utils.html_report import _relative_path
        result = _relative_path("/var/log/test.png", "reports")
        assert result is None


# ---------------------------------------------------------------------------
# HTML-09: html.escape() prevents XSS in error messages and field values
# ---------------------------------------------------------------------------

class TestHtmlEscape:
    def test_script_tag_in_error_message_is_escaped(self):
        from src.utils.html_report import build_step_table
        step = _make_step(
            status="failed",
            error_message="<script>alert(1)</script>",
            failure_phase="interaction",
        )
        summary = _make_summary([step])
        html = build_step_table(summary)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_angle_brackets_in_element_name_are_escaped(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(element_name="<button>")
        html = _step_row_html(step)
        assert "<button>" not in html
        assert "&lt;button&gt;" in html

    def test_ampersand_in_tab_name_is_escaped(self):
        from src.utils.html_report import _step_row_html
        step = _make_step(tab_name="A&B")
        html = _step_row_html(step)
        assert "A&amp;B" in html
