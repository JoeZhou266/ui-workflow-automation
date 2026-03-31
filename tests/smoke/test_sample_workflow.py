"""Smoke test — runs the sample workflow against a real browser.

Requires:
  - Chrome installed
  - Pass --workflow testdata/workflows/sample_workflow.json (or any workflow JSON)
  - Optionally pass --headless to suppress the browser window

Run with:
    pytest tests/smoke/test_sample_workflow.py \\
        --workflow testdata/workflows/sample_workflow.json \\
        --headless -v

This test is skipped automatically if --workflow is not provided.
"""
from __future__ import annotations

import pytest

from src.core.enums import StepStatus
from src.workflow.workflow_engine import WorkflowEngine


pytestmark = pytest.mark.smoke


def test_workflow_runs_without_crash(driver, workflow_definition, app_config):
    """Execute the workflow and assert no steps ended in FAILED status."""
    engine = WorkflowEngine(
        driver=driver,
        definition=workflow_definition,
        base_url=app_config.base_url,
        default_wait_timeout=app_config.explicit_wait_timeout,
        screenshots_dir=app_config.screenshots_dir,
    )

    summary = engine.run()

    # Print summary for visibility in CI logs
    print(f"\n{'='*60}")
    print(f"Workflow: {summary.workflow_name}")
    print(f"Total: {summary.total} | Passed: {summary.passed} | "
          f"Failed: {summary.failed} | Skipped: {summary.skipped}")
    if summary.duration_seconds is not None:
        print(f"Duration: {summary.duration_seconds:.1f}s")
    print(f"Pass rate: {summary.passed_rate:.1f}%")

    if summary.failed > 0:
        print("\nFailed steps:")
        for step in summary.steps:
            if step.status == StepStatus.FAILED:
                print(f"  - {step.location}")
                print(f"    Phase: {step.failure_phase}")
                print(f"    Error: {step.error_message}")
                if step.screenshot_path:
                    print(f"    Screenshot: {step.screenshot_path}")
    print("=" * 60)

    assert summary.failed == 0, (
        f"{summary.failed} step(s) failed in workflow '{summary.workflow_name}'. "
        "See output above for details."
    )
