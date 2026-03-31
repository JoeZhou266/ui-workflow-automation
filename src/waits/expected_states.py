from __future__ import annotations

from typing import Callable, Optional, Tuple

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC


# ---------------------------------------------------------------------------
# Type alias for a callable that returns truthy/falsy like an ExpectedCondition
# ---------------------------------------------------------------------------
Condition = Callable[[WebDriver], object]


def element_text_equals(locator: Tuple[str, str], text: str) -> Condition:
    """Wait until element text exactly matches ``text``."""
    def _condition(driver: WebDriver) -> bool:
        try:
            el = driver.find_element(*locator)
            return el.text.strip() == text
        except StaleElementReferenceException:
            return False
    return _condition


def element_text_contains(locator: Tuple[str, str], text: str) -> Condition:
    """Wait until element text contains ``text``."""
    def _condition(driver: WebDriver) -> bool:
        try:
            el = driver.find_element(*locator)
            return text in el.text
        except StaleElementReferenceException:
            return False
    return _condition


def element_value_equals(locator: Tuple[str, str], value: str) -> Condition:
    """Wait until element ``value`` attribute equals ``value``."""
    def _condition(driver: WebDriver) -> bool:
        try:
            el = driver.find_element(*locator)
            return (el.get_attribute("value") or "") == value
        except StaleElementReferenceException:
            return False
    return _condition


def element_attribute_equals(
    locator: Tuple[str, str], attr: str, value: str
) -> Condition:
    """Wait until ``attr`` attribute of element equals ``value``."""
    def _condition(driver: WebDriver) -> bool:
        try:
            el = driver.find_element(*locator)
            return (el.get_attribute(attr) or "") == value
        except StaleElementReferenceException:
            return False
    return _condition


def element_attribute_contains(
    locator: Tuple[str, str], attr: str, value: str
) -> Condition:
    """Wait until ``attr`` attribute of element contains ``value``."""
    def _condition(driver: WebDriver) -> bool:
        try:
            el = driver.find_element(*locator)
            return value in (el.get_attribute(attr) or "")
        except StaleElementReferenceException:
            return False
    return _condition


def element_count_greater_than(locator: Tuple[str, str], count: int) -> Condition:
    """Wait until the number of matching elements exceeds ``count``."""
    def _condition(driver: WebDriver) -> bool:
        try:
            elements = driver.find_elements(*locator)
            return len(elements) > count
        except StaleElementReferenceException:
            return False
    return _condition


def options_count_greater_than(locator: Tuple[str, str], count: int) -> Condition:
    """Wait until a ``<select>`` element has more than ``count`` ``<option>`` children."""
    def _condition(driver: WebDriver) -> bool:
        try:
            el = driver.find_element(*locator)
            options = el.find_elements("tag name", "option")
            return len(options) > count
        except StaleElementReferenceException:
            return False
    return _condition


def element_gone(locator: Tuple[str, str]) -> Condition:
    """Wait until element is no longer visible (spinner / overlay gone)."""
    return EC.invisibility_of_element_located(locator)


def element_enabled(locator: Tuple[str, str]) -> Condition:
    """Wait until element is present, visible, and enabled."""
    def _condition(driver: WebDriver) -> bool:
        try:
            el = driver.find_element(*locator)
            return el.is_displayed() and el.is_enabled()
        except StaleElementReferenceException:
            return False
    return _condition
