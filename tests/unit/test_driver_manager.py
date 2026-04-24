"""Unit tests for DriverManager path threading — no browser required."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.driver.driver_manager import DriverManager


def _make_config(driver_path=None, binary_path=None):
    config = MagicMock()
    config.browser = "chrome"
    config.headless = False
    config.window_width = 1920
    config.window_height = 1080
    config.page_load_timeout = 30
    config.implicit_wait = 0
    config.driver_path = driver_path
    config.browser_binary_path = binary_path
    return config


class TestDriverManagerPaths:

    @patch("src.driver.driver_manager.DriverFactory.create")
    def test_driver_path_from_config_is_passed_to_factory(self, mock_create):
        mock_create.return_value = MagicMock()
        manager = DriverManager(_make_config(driver_path="/usr/local/bin/chromedriver"))
        manager.start()
        assert mock_create.call_args.kwargs["driver_path"] == "/usr/local/bin/chromedriver"

    @patch("src.driver.driver_manager.DriverFactory.create")
    def test_constructor_driver_path_takes_priority_over_config(self, mock_create):
        mock_create.return_value = MagicMock()
        config = _make_config(driver_path="/config/chromedriver")
        manager = DriverManager(config, driver_path="/explicit/chromedriver")
        manager.start()
        assert mock_create.call_args.kwargs["driver_path"] == "/explicit/chromedriver"

    @patch("src.driver.driver_manager.DriverFactory.create")
    def test_binary_path_from_config_is_passed_to_factory(self, mock_create):
        mock_create.return_value = MagicMock()
        manager = DriverManager(_make_config(binary_path="/opt/google/chrome"))
        manager.start()
        assert mock_create.call_args.kwargs["binary_path"] == "/opt/google/chrome"

    @patch("src.driver.driver_manager.DriverFactory.create")
    def test_none_paths_when_config_has_none(self, mock_create):
        mock_create.return_value = MagicMock()
        manager = DriverManager(_make_config())
        manager.start()
        assert mock_create.call_args.kwargs["driver_path"] is None
        assert mock_create.call_args.kwargs["binary_path"] is None
