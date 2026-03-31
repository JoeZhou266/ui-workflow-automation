from __future__ import annotations

from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.logger import get_logger
from src.models.workflow_models import LoadCriteria, PageDefinition
from src.ui.base_page import BasePage
from src.utils.screenshots import ScreenshotManager
from src.waits.wait_manager import WaitManager

logger = get_logger("dynamic_page")


class DynamicPage(BasePage):
    """A page driven entirely by a :class:`PageDefinition` JSON model.

    No hardcoded locators — all readiness criteria come from the model.
    """

    def __init__(
        self,
        driver: WebDriver,
        wait_manager: WaitManager,
        page_def: PageDefinition,
        screenshot_manager: Optional[ScreenshotManager] = None,
    ) -> None:
        super().__init__(driver, wait_manager, screenshot_manager)
        self._page_def = page_def

    @property
    def name(self) -> str:
        return self._page_def.name

    @property
    def load_criteria(self) -> Optional[LoadCriteria]:
        return self._page_def.load_criteria

    def ensure_ready(self, tab_name: str = "") -> None:
        """Wait for this page to be fully loaded according to its load_criteria."""
        logger.info("Ensuring page ready: %s", self.name)
        self.wait_for_page_ready(
            self.load_criteria,
            page_name=self.name,
            tab_name=tab_name,
        )
