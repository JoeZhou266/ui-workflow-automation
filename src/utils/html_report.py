from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Optional

from src.core.constants import HTML_REPORT_DIR
from src.core.enums import StepStatus
from src.models.element_models import ExecutionSummary, StepResult

# Map StepStatus to row background colors (Bootstrap-inspired palette)
_STATUS_COLORS = {
    StepStatus.PASSED: "#d4edda",    # green
    StepStatus.FAILED: "#f8d7da",    # red
    StepStatus.SKIPPED: "#fff3cd",   # yellow
}


def build_step_table(
    summary: ExecutionSummary,
    reports_dir: str = HTML_REPORT_DIR,
) -> str:
    """Return a self-contained <details> HTML block for embedding in pytest-html extras.

    Args:
        summary: ExecutionSummary from ResultCollector.
        reports_dir: Root directory that report HTML file lives in (default: constants.HTML_REPORT_DIR).
                     Used to compute relative paths for screenshots.

    Returns:
        HTML string starting with <details> and ending with </details>.
    """
    total = summary.total
    passed = summary.passed
    failed = summary.failed
    skipped = summary.skipped

    header = (
        f"Workflow: {escape(summary.workflow_name)} — "
        f"{total} steps: {passed} passed, {failed} failed, {skipped} skipped"
    )
    rows = "".join(_step_row_html(step, reports_dir) for step in summary.steps)

    return (
        "<details>"
        f"<summary><b>{header}</b></summary>"
        '<table style="width:100%;border-collapse:collapse;font-size:0.85em">'
        "<tr>"
        "<th>Status</th><th>Tab</th><th>Page</th><th>Section</th>"
        "<th>Element</th><th>Action</th><th>Duration (ms)</th>"
        "<th>Error / Phase</th><th>Screenshot</th>"
        "</tr>"
        f"{rows}"
        "</table>"
        "</details>"
    )


def _step_row_html(
    step: StepResult,
    reports_dir: str = HTML_REPORT_DIR,
) -> str:
    """Return a single <tr> HTML string for one StepResult row.

    Args:
        step: StepResult with all fields populated.
        reports_dir: Root directory for relative path computation.

    Returns:
        HTML <tr>...</tr> string with background color and content cells.
    """
    color = _STATUS_COLORS.get(step.status, "#ffffff")
    duration = f"{step.duration_ms:.0f}" if step.duration_ms is not None else "—"

    error_cell = ""
    if step.status == StepStatus.FAILED:
        err = escape(step.error_message or "")
        phase = escape(str(step.failure_phase.value if step.failure_phase else ""))
        error_cell = f"{err}<br><small>phase: {phase}</small>"

    screenshot_cell = ""
    if step.screenshot_path:
        rel = _relative_path(step.screenshot_path, reports_dir)
        if rel:
            esc_rel = escape(rel)
            screenshot_cell = (
                f'<a href="{esc_rel}" target="_blank">'
                f'<img src="{esc_rel}" style="max-width:200px" /></a>'
            )

    return (
        f'<tr style="background:{color}">'
        f"<td>{escape(step.status.value)}</td>"
        f"<td>{escape(step.tab_name)}</td>"
        f"<td>{escape(step.page_name)}</td>"
        f"<td>{escape(step.section_name)}</td>"
        f"<td>{escape(step.element_name)}</td>"
        f"<td>{escape(step.action.value)}</td>"
        f"<td>{duration}</td>"
        f"<td>{error_cell}</td>"
        f"<td>{screenshot_cell}</td>"
        "</tr>"
    )


def _relative_path(abs_path: str, reports_dir: str) -> Optional[str]:
    """Return path relative to reports_dir, or None if path is outside reports_dir.

    Security: Path.relative_to() raises ValueError if abs_path doesn't start
    with reports_dir. We catch and return None, preventing path traversal in
    href/src attributes.

    Args:
        abs_path: Absolute or relative path to the artifact file.
        reports_dir: Root directory (e.g. "reports").

    Returns:
        Relative path string (e.g. "screenshots/foo.png") or None.
    """
    try:
        return str(Path(abs_path).relative_to(reports_dir))
    except ValueError:
        return None
