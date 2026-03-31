from __future__ import annotations

import os
from typing import Optional

import pytest

from src.core.config import AppConfig
from src.core.logger import configure_logging


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
