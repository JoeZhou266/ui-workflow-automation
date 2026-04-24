"""Unit tests for DriverFactory binary_path — no browser required."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.driver.driver_factory import DriverFactory


class TestDriverFactoryBinaryPath:
    """Verify options.binary_location is set iff binary_path is provided."""

    # --- Chrome ---

    @patch("selenium.webdriver.Chrome")
    @patch("src.driver.driver_factory.ChromeService")
    def test_chrome_sets_binary_location_when_provided(self, mock_service, mock_chrome):
        mock_chrome.return_value = MagicMock()
        DriverFactory._create_chrome(
            headless=False, width=1920, height=1080,
            driver_path="/fake/chromedriver", binary_path="/opt/chrome",
        )
        options = mock_chrome.call_args.kwargs["options"]
        assert options.binary_location == "/opt/chrome"

    @patch("selenium.webdriver.Chrome")
    @patch("src.driver.driver_factory.ChromeService")
    def test_chrome_binary_location_unchanged_when_none(self, mock_service, mock_chrome):
        mock_chrome.return_value = MagicMock()
        DriverFactory._create_chrome(
            headless=False, width=1920, height=1080,
            driver_path="/fake/chromedriver", binary_path=None,
        )
        options = mock_chrome.call_args.kwargs["options"]
        assert options.binary_location == ""  # Selenium 4 default

    # --- Firefox ---

    @patch("selenium.webdriver.Firefox")
    @patch("src.driver.driver_factory.FirefoxService")
    def test_firefox_sets_binary_location_when_provided(self, mock_service, mock_firefox):
        mock_firefox.return_value = MagicMock()
        DriverFactory._create_firefox(
            headless=False, width=1920, height=1080,
            driver_path="/fake/geckodriver", binary_path="/usr/bin/firefox",
        )
        options = mock_firefox.call_args.kwargs["options"]
        assert options.binary_location == "/usr/bin/firefox"

    @patch("selenium.webdriver.Firefox")
    @patch("src.driver.driver_factory.FirefoxService")
    def test_firefox_binary_location_unchanged_when_none(self, mock_service, mock_firefox):
        mock_firefox.return_value = MagicMock()
        DriverFactory._create_firefox(
            headless=False, width=1920, height=1080,
            driver_path="/fake/geckodriver", binary_path=None,
        )
        options = mock_firefox.call_args.kwargs["options"]
        assert options.binary_location == ""

    # --- Edge ---

    @patch("selenium.webdriver.Edge")
    @patch("src.driver.driver_factory.EdgeService")
    def test_edge_sets_binary_location_when_provided(self, mock_service, mock_edge):
        mock_edge.return_value = MagicMock()
        DriverFactory._create_edge(
            headless=False, width=1920, height=1080,
            driver_path="/fake/msedgedriver", binary_path="/usr/bin/msedge",
        )
        options = mock_edge.call_args.kwargs["options"]
        assert options.binary_location == "/usr/bin/msedge"

    @patch("selenium.webdriver.Edge")
    @patch("src.driver.driver_factory.EdgeService")
    def test_edge_binary_location_unchanged_when_none(self, mock_service, mock_edge):
        mock_edge.return_value = MagicMock()
        DriverFactory._create_edge(
            headless=False, width=1920, height=1080,
            driver_path="/fake/msedgedriver", binary_path=None,
        )
        options = mock_edge.call_args.kwargs["options"]
        assert options.binary_location == ""

    # --- create() dispatches binary_path ---

    @patch("selenium.webdriver.Chrome")
    @patch("src.driver.driver_factory.ChromeService")
    def test_create_passes_binary_path_to_chrome(self, mock_service, mock_chrome):
        mock_instance = MagicMock()
        mock_chrome.return_value = mock_instance
        DriverFactory.create(
            browser="chrome",
            driver_path="/fake/chromedriver",
            binary_path="/opt/chrome",
        )
        options = mock_chrome.call_args.kwargs["options"]
        assert options.binary_location == "/opt/chrome"
