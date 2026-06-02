from __future__ import annotations

import datetime
import os
import warnings
from pathlib import Path
from typing import Optional

import coverage as _cov_mod
import pytest
from pytest import CollectReport, StashKey
from pytest_html import extras as html_extras

from src.core.config import AppConfig
from src.core.constants import COVERAGE_DIR, HTML_REPORT_DATE_FORMAT, HTML_REPORT_DIR
from src.utils.coverage_index import build_custom_index
from src.core.logger import configure_logging
from src.models.element_models import ExecutionSummary
from src.utils.files import ensure_dir, safe_filename
from src.utils.html_report import build_step_table


# ---------------------------------------------------------------------------
# Test outcome stash (populated by hook, read by video_recorder teardown)
# ---------------------------------------------------------------------------

_phase_report_key: StashKey[dict[str, CollectReport]] = StashKey()

# ---------------------------------------------------------------------------
# HTML report stash keys (populated by fixtures, read by makereport hook)
# ---------------------------------------------------------------------------

_execution_summary_key: StashKey[ExecutionSummary] = StashKey()
_video_path_key: StashKey[Optional[str]] = StashKey()


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Dynamically set --html report path before pytest-html reads it.

    Sets config.option.htmlpath to a timestamped path so pytest-html generates
    a new file on every run (D-08, D-09). Uses tryfirst=True to run before
    pytest-html's own pytest_configure reads htmlpath.

    Uses skip=True on getoption to avoid ValueError when --workflow is not yet
    registered (pytest_addoption runs after some pytest_configure invocations).
    """
    workflow_path = config.getoption("--workflow", default=None, skip=True)
    if workflow_path:
        workflow_name = safe_filename(Path(workflow_path).stem)
    else:
        workflow_name = "run"
    timestamp = datetime.datetime.now().strftime(HTML_REPORT_DATE_FORMAT)
    filename = f"{workflow_name}_report_{timestamp}.html"
    report_dir = Path(HTML_REPORT_DIR)
    ensure_dir(report_dir)
    config.option.htmlpath = str(report_dir / filename)
    # Do NOT set self_contained_html=True — relative screenshot links break in that mode
    # (RESEARCH.md Pitfall 3 / CONTEXT.md D-05)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Store each phase report in item.stash so fixtures can read pass/fail outcome."""
    rep = yield   # new-style wrapper — yield returns the report directly
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep

    # Attach workflow step drill-down and video link on teardown phase
    if rep.when == "teardown":
        summary = item.stash.get(_execution_summary_key, None)
        video_path = item.stash.get(_video_path_key, None)
        coverage_index = Path(HTML_REPORT_DIR) / "coverage" / "index.html"
        if summary is not None or video_path is not None or coverage_index.exists():
            html_parts = []
            if summary is not None:
                html_parts.append(build_step_table(summary))
            if video_path is not None:
                rel = Path(video_path).name
                html_parts.append(
                    f'<p><a href="videos/{rel}" target="_blank">&#9654; Video</a></p>'
                )
            # D-08, D-09, D-10: coverage link — only when reports/coverage/index.html exists
            if coverage_index.exists():
                html_parts.append(
                    '<p><a href="coverage/index.html" target="_blank">Coverage Report</a></p>'
                )
            html_str = "".join(html_parts)
            existing = list(getattr(rep, "extras", []) or [])
            rep.extras = existing + [html_extras.html(html_str)]

    return rep


def pytest_sessionfinish(session, exitstatus):
    """Generate reports/coverage/custom_index.html after coverage HTML is written (D-13).

    Hook ordering: pytest-cov writes coverage HTML inside pytest_runtestloop
    (before pytest_sessionfinish fires), so reports/coverage/ and .coverage
    are both available here.

    Fail-open: any exception warns and skips generation; never fails the session.
    """
    config = session.config
    # D-11: respect --no-cov (pytest-cov stores this as config.option.no_cov)
    if getattr(config.option, "no_cov", False):
        return

    # D-14: skip gracefully when .coverage binary doesn't exist.
    # Resolve data_file via coverage.py config so COVERAGE_FILE env and .coveragerc
    # [run] data_file are both respected (WR-03).
    _data_file = _cov_mod.Coverage().config.data_file
    if not Path(_data_file).exists():
        return

    try:
        html = build_custom_index(coverage_dir=COVERAGE_DIR, data_file=_data_file)
        out = Path(COVERAGE_DIR) / "custom_index.html"
        out.write_text(html, encoding="utf-8")
    except Exception as exc:
        warnings.warn(f"coverage_index: failed to generate custom_index.html: {exc}")


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default="dev",
        help="Environment name (matches configs/env.<name>.yaml). Default: dev",
    )
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode.",
    )
    parser.addoption(
        "--workflow",
        action="store",
        default=None,
        help="Path to a workflow JSON file for smoke tests.",
    )
    parser.addoption(
        "--browser",
        action="store",
        default=None,
        help="Browser override: chrome | firefox | edge",
    )


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app_config(request) -> AppConfig:
    """Session-scoped configuration loaded from YAML + env vars."""
    env = request.config.getoption("--env")
    config = AppConfig(env=env)

    # CLI overrides
    if request.config.getoption("--headless"):
        config.headless = True
    browser_override = request.config.getoption("--browser")
    if browser_override:
        config.browser = browser_override.lower()

    configure_logging(config.log_level, config.log_file_path)
    return config


@pytest.fixture(scope="function")
def driver(app_config: AppConfig):
    """Function-scoped WebDriver. Created fresh for each test and quit on teardown."""
    from src.driver.driver_manager import DriverManager
    manager = DriverManager(app_config)
    web_driver = manager.start()
    yield web_driver
    manager.stop()


@pytest.fixture(scope="function")
def video_recorder(request, app_config: AppConfig, driver):
    """Start video recording; retain file only on test failure.

    Opt-in: tests must explicitly request this fixture.
    On PASS: video file is deleted.
    On FAIL: video file is retained in reports/videos/.
    When recording is unavailable (headless, ffmpeg absent, record_video=False):
    yields None and no-ops silently.
    """
    from src.utils.videos import VideoManager
    from src.core.logger import get_logger

    _log = get_logger("video_recorder")
    manager = VideoManager(base_dir=app_config.videos_dir)
    video_path = manager.start(request.node.name, headless=app_config.headless or not app_config.record_video)
    yield video_path

    # --- teardown: read outcome from stash ---
    # The pytest_runtest_makereport hook populates this stash BEFORE teardown runs.
    report = request.node.stash.get(_phase_report_key, {})

    class _Pass:
        """Sentinel report with no failure — used when stash key is absent."""
        failed = False
        skipped = False

    call_report = report.get("call", _Pass())
    setup_report = report.get("setup", _Pass())
    test_failed = call_report.failed or setup_report.failed

    manager.stop()

    if video_path:
        if test_failed:
            _log.info("Video retained (test failed): %s", video_path)
            request.node.stash[_video_path_key] = video_path
        else:
            manager.delete(video_path)


@pytest.fixture(scope="function")
def workflow_definition(request):
    """Load a WorkflowDefinition from --workflow path, or skip if not provided."""
    from src.data.json_loader import WorkflowLoader
    from src.data.validators import WorkflowValidator

    path = request.config.getoption("--workflow")
    if not path:
        pytest.skip("No --workflow path provided")

    definition = WorkflowLoader.load(path)
    WorkflowValidator().validate_or_raise(definition)
    return definition


@pytest.fixture(scope="function")
def workflow_report_extras(request):
    """Register an ExecutionSummary for per-test HTML drill-down.

    Opt-in: tests must explicitly request this fixture.
    Calling the yielded function stores the summary in item.stash so the
    pytest_runtest_makereport teardown hook can build the HTML extras table.

    Usage in smoke tests:
        def test_foo(driver, workflow_definition, app_config, workflow_report_extras):
            engine = WorkflowEngine(...)
            summary = engine.run()
            workflow_report_extras(summary)
            assert summary.failed == 0
    """
    def _register(summary: ExecutionSummary) -> None:
        request.node.stash[_execution_summary_key] = summary

    yield _register
