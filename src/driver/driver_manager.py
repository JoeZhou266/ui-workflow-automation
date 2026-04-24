from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.config import AppConfig
from src.core.logger import get_logger
from src.driver.driver_factory import DriverFactory

logger = get_logger("driver_manager")


class DriverManager:
    """Context manager that owns the WebDriver lifecycle.

    Usage::

        config = AppConfig()
        with DriverManager(config) as driver:
            driver.get("https://example.com")
    """

    def __init__(self, config: AppConfig, driver_path: Optional[str] = None) -> None:
        self._config = config
        self._driver_path = driver_path or config.driver_path
        self._binary_path = config.browser_binary_path
        self._driver: Optional[WebDriver] = None

    def start(self) -> WebDriver:
        """Create the driver. Called automatically by the context manager."""
        self._driver = DriverFactory.create(
            browser=self._config.browser,
            headless=self._config.headless,
            window_width=self._config.window_width,
            window_height=self._config.window_height,
            page_load_timeout=self._config.page_load_timeout,
            implicit_wait=self._config.implicit_wait,
            driver_path=self._driver_path,
            binary_path=self._binary_path,
        )
        logger.info("WebDriver started: %s", self._config.browser)
        return self._driver

    def stop(self) -> None:
        """Quit the driver. Called automatically by the context manager."""
        if self._driver is not None:
            try:
                self._driver.quit()
                logger.info("WebDriver stopped")
            except Exception as exc:
                logger.warning("Error during driver quit: %s", exc)
            finally:
                self._driver = None

    @property
    def driver(self) -> Optional[WebDriver]:
        return self._driver

    def __enter__(self) -> WebDriver:
        return self.start()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()
