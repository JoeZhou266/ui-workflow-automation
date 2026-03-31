from __future__ import annotations

from urllib.parse import urljoin

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.logger import get_logger
from src.models.workflow_models import PageDefinition

logger = get_logger("navigator")


class Navigator:
    """Handles browser URL navigation for the workflow engine."""

    def __init__(self, driver: WebDriver, base_url: str = "") -> None:
        self._driver = driver
        self._base_url = base_url.rstrip("/")

    def open_start_url(self, start_url: str) -> None:
        """Navigate to the workflow start URL."""
        url = self._resolve_url(start_url)
        logger.info("Navigating to start URL: %s", url)
        self._driver.get(url)

    def navigate_to_page(self, page: PageDefinition) -> None:
        """Navigate to a page's path if one is defined.

        If the page has no path, navigation is skipped (assumed the app
        handles routing via UI interaction).
        """
        if not page.path:
            logger.debug("Page '%s' has no path — skipping URL navigation", page.name)
            return
        url = self._resolve_url(page.path)
        logger.info("Navigating to page '%s': %s", page.name, url)
        self._driver.get(url)

    def _resolve_url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        if self._base_url:
            return urljoin(self._base_url + "/", path.lstrip("/"))
        return path
