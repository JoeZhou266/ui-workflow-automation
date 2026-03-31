from __future__ import annotations

from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.logger import get_logger
from src.models.workflow_models import SectionDefinition
from src.ui.base_component import BaseComponent
from src.utils.screenshots import ScreenshotManager
from src.waits.wait_manager import WaitManager

logger = get_logger("dynamic_section")


class DynamicSection(BaseComponent):
    """A section/component driven by a :class:`SectionDefinition` JSON model."""

    def __init__(
        self,
        driver: WebDriver,
        wait_manager: WaitManager,
        section_def: SectionDefinition,
        screenshot_manager: Optional[ScreenshotManager] = None,
    ) -> None:
        super().__init__(
            driver,
            wait_manager,
            root_locator=section_def.locator,
            screenshot_manager=screenshot_manager,
        )
        self._section_def = section_def

    @property
    def name(self) -> str:
        return self._section_def.name
