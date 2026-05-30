from __future__ import annotations

import os
from typing import Optional

import pytest
from pytest import CollectReport, StashKey

from src.core.config import AppConfig
from src.core.logger import configure_logging


# ---------------------------------------------------------------------------
# Test outcome stash (populated by hook, read by video_recorder teardown)
# ---------------------------------------------------------------------------

_phase_report_key: StashKey[dict[str, CollectReport]] = StashKey()


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Store each phase report in item.stash so fixtures can read pass/fail outcome."""
    rep = yield   # new-style wrapper — yield returns the report directly
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep
    return rep


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

    configure_logging(config.log_level)
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
    manager = VideoManager()
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

    if video_path:
        if test_failed:
            _log.info("Video retained (test failed): %s", video_path)
        else:
            manager.delete(video_path)

    manager.stop()


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
