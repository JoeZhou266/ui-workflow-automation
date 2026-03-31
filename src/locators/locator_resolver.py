from __future__ import annotations

from typing import Tuple

from selenium.webdriver.common.by import By

from src.core.exceptions import LocatorResolutionError
from src.models.workflow_models import LocatorDefinition

# Maps JSON 'by' strings to Selenium By constants
_BY_MAP: dict[str, str] = {
    "id": By.ID,
    "name": By.NAME,
    "class_name": By.CLASS_NAME,
    "css_selector": By.CSS_SELECTOR,
    "xpath": By.XPATH,
    "link_text": By.LINK_TEXT,
    "partial_link_text": By.PARTIAL_LINK_TEXT,
    "tag_name": By.TAG_NAME,
}


class LocatorResolver:
    """Translates :class:`LocatorDefinition` objects into Selenium ``(By, value)`` tuples."""

    @staticmethod
    def resolve(locator: LocatorDefinition, element_name: str = "") -> Tuple[str, str]:
        """Convert a :class:`LocatorDefinition` to a ``(By, selector)`` tuple.

        Args:
            locator: The locator definition from JSON.
            element_name: Optional name of the element for error context.

        Returns:
            A ``(selenium.webdriver.common.by.By, selector_string)`` tuple.

        Raises:
            LocatorResolutionError: If the ``by`` value is not recognised.
        """
        by_key = locator.by.lower().strip()
        selenium_by = _BY_MAP.get(by_key)
        if selenium_by is None:
            raise LocatorResolutionError(by=locator.by, element_name=element_name)
        return selenium_by, locator.value

    @staticmethod
    def supported_strategies() -> list[str]:
        """Return the list of supported locator strategy names."""
        return list(_BY_MAP.keys())
