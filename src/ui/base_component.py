from __future__ import annotations

from typing import List, Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from src.core.logger import get_logger
from src.models.workflow_models import LocatorDefinition
from src.locators.locator_resolver import LocatorResolver
from src.ui.base_page import BasePage
from src.utils.screenshots import ScreenshotManager
from src.waits.wait_manager import WaitManager

logger = get_logger("base_component")


class BaseComponent(BasePage):
    """A section/component scoped to a container element.

    Extends :class:`BasePage` so all the same interaction helpers are available,
    but ``find()`` and ``find_all()`` are resolved within the container's DOM
    subtree when a root locator is provided.
    """

    def __init__(
        self,
        driver: WebDriver,
        wait_manager: WaitManager,
        root_locator: Optional[LocatorDefinition] = None,
        screenshot_manager: Optional[ScreenshotManager] = None,
    ) -> None:
        super().__init__(driver, wait_manager, screenshot_manager)
        self._root_locator = root_locator
        self._root_element: Optional[WebElement] = None

    def get_root(self) -> Optional[WebElement]:
        """Return the container element, or ``None`` if no root locator is set."""
        if self._root_locator is None:
            return None
        loc = LocatorResolver.resolve(self._root_locator)
        self._root_element = self._wm.wait_present(loc)  # type: ignore[assignment]
        return self._root_element

    def find_in_root(self, locator: LocatorDefinition, name: str = "") -> WebElement:
        """Find an element scoped to the component root container.

        Falls back to a page-level search if no root locator is configured.
        """
        root = self.get_root()
        if root is None:
            return self.find(locator, name)
        loc = LocatorResolver.resolve(locator, name)
        return root.find_element(*loc)

    def find_all_in_root(self, locator: LocatorDefinition) -> List[WebElement]:
        """Find all elements scoped to the component root container."""
        root = self.get_root()
        if root is None:
            return self.find_all(locator)
        loc = LocatorResolver.resolve(locator)
        return root.find_elements(*loc)
