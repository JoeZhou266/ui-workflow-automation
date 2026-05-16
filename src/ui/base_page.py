from __future__ import annotations

import time
from typing import Callable, List, Optional, Tuple, TypeVar

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select

from src.core.constants import DEFAULT_STALE_RETRY_COUNT
from src.core.exceptions import ElementActionError
from src.core.logger import get_logger
from src.models.workflow_models import LocatorDefinition, LoadCriteria
from src.locators.locator_resolver import LocatorResolver
from src.utils.screenshots import ScreenshotManager
from src.waits.page_readiness import PageReadinessChecker
from src.waits.wait_manager import WaitManager

T = TypeVar("T")
logger = get_logger("base_page")


class BasePage:
    """Provides all core Selenium interaction primitives.

    All element interaction logic is centralised here.  Subclasses and the
    action engine delegate to these methods rather than calling the WebDriver
    directly.
    """

    def __init__(
        self,
        driver: WebDriver,
        wait_manager: WaitManager,
        screenshot_manager: Optional[ScreenshotManager] = None,
    ) -> None:
        self._driver = driver
        self._wm = wait_manager
        self._screenshots = screenshot_manager or ScreenshotManager()
        self._readiness = PageReadinessChecker(driver, wait_manager)

    # ------------------------------------------------------------------
    # Finding elements
    # ------------------------------------------------------------------

    def find(self, locator: LocatorDefinition, name: str = "") -> WebElement:
        """Find a single element. Waits for presence before returning."""
        loc = LocatorResolver.resolve(locator, name)
        return self._wm.wait_present(loc)  # type: ignore[return-value]

    def find_all(self, locator: LocatorDefinition) -> List[WebElement]:
        """Find all matching elements without waiting."""
        loc = LocatorResolver.resolve(locator)
        return self._driver.find_elements(*loc)

    # ------------------------------------------------------------------
    # Visibility / state
    # ------------------------------------------------------------------

    def is_visible(self, locator: LocatorDefinition) -> bool:
        """Return ``True`` if the element is present and visible, without waiting."""
        try:
            loc = LocatorResolver.resolve(locator)
            el = self._driver.find_element(*loc)
            return el.is_displayed()
        except Exception:
            return False

    def get_text(self, locator: LocatorDefinition, name: str = "") -> str:
        """Return stripped text content of an element."""
        el = self.find(locator, name)
        return el.text.strip()

    def get_attribute(self, locator: LocatorDefinition, attr: str, name: str = "") -> Optional[str]:
        el = self.find(locator, name)
        return el.get_attribute(attr)

    # ------------------------------------------------------------------
    # Waits (delegating to WaitManager)
    # ------------------------------------------------------------------

    def wait_for_visible(
        self, locator: LocatorDefinition, timeout: Optional[int] = None
    ) -> WebElement:
        loc = LocatorResolver.resolve(locator)
        return self._wm.wait_visible(loc, timeout=timeout)  # type: ignore[return-value]

    def wait_for_clickable(
        self, locator: LocatorDefinition, timeout: Optional[int] = None
    ) -> WebElement:
        loc = LocatorResolver.resolve(locator)
        return self._wm.wait_clickable(loc, timeout=timeout)  # type: ignore[return-value]

    def wait_for_present(
        self, locator: LocatorDefinition, timeout: Optional[int] = None
    ) -> WebElement:
        loc = LocatorResolver.resolve(locator)
        return self._wm.wait_present(loc, timeout=timeout)  # type: ignore[return-value]

    def wait_for_document_ready(self) -> None:
        self._wm.wait_document_ready()

    def wait_for_ajax_idle(self) -> None:
        self._wm.wait_ajax_idle()

    def wait_for_page_ready(
        self,
        load_criteria: Optional[LoadCriteria],
        page_name: str = "",
        tab_name: str = "",
    ) -> None:
        self._readiness.wait_for_page_ready(load_criteria, page_name, tab_name)

    def wait_for_spinner_gone(self, locator: LocatorDefinition) -> None:
        loc = LocatorResolver.resolve(locator)
        from src.waits.expected_states import element_gone
        try:
            self._wm.wait_for(element_gone(loc), "spinner gone")
        except Exception:
            pass  # best-effort

    def wait_for_overlay_gone(self, locator: LocatorDefinition) -> None:
        self.wait_for_spinner_gone(locator)  # same logic

    def wait_for_text(
        self, locator: LocatorDefinition, expected_text: str, timeout: Optional[int] = None
    ) -> None:
        loc = LocatorResolver.resolve(locator)
        from src.waits.expected_states import element_text_contains
        self._wm.wait_for(
            element_text_contains(loc, expected_text),
            f"text contains '{expected_text}'",
            timeout=timeout,
        )

    def wait_for_count(
        self, locator: LocatorDefinition, minimum_count: int, timeout: Optional[int] = None
    ) -> None:
        loc = LocatorResolver.resolve(locator)
        from src.waits.expected_states import element_count_greater_than
        self._wm.wait_for(
            element_count_greater_than(loc, minimum_count - 1),
            f"count >= {minimum_count}",
            timeout=timeout,
        )

    def wait_for_options_count(
        self, locator: LocatorDefinition, minimum_count: int, timeout: Optional[int] = None
    ) -> None:
        loc = LocatorResolver.resolve(locator)
        from src.waits.expected_states import options_count_greater_than
        self._wm.wait_for(
            options_count_greater_than(loc, minimum_count - 1),
            f"options count >= {minimum_count}",
            timeout=timeout,
        )

    def wait_for_attribute(
        self,
        locator: LocatorDefinition,
        name: str,
        value: str,
        timeout: Optional[int] = None,
    ) -> None:
        loc = LocatorResolver.resolve(locator)
        from src.waits.expected_states import element_attribute_equals
        self._wm.wait_for(
            element_attribute_equals(loc, name, value),
            f"attribute '{name}' == '{value}'",
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def click(self, locator: LocatorDefinition, name: str = "") -> None:
        """Wait for element visible then click it."""
        el = self.wait_for_visible(locator)
        el.click()

    def safe_click(self, locator: LocatorDefinition, name: str = "") -> None:
        """Scroll into view, wait for clickable, click, retry once on intercept."""
        el = self.wait_for_visible(locator)
        self.scroll_into_view(el)
        el = self.wait_for_clickable(locator)
        try:
            el.click()
        except ElementClickInterceptedException:
            logger.debug("Click intercepted for '%s' — retrying after short pause", name)
            # Brief pause to allow overlay to clear, then re-locate and retry
            time.sleep(0.5)  # narrowly scoped fallback: overlay may still be animating
            el = self.wait_for_clickable(locator)
            el.click()

    def type_text(self, locator: LocatorDefinition, text: str, name: str = "") -> None:
        """Find the element and send keys without clearing first."""
        el = self.wait_for_visible(locator)
        el.send_keys(text)

    def clear_and_type(
        self,
        locator: LocatorDefinition,
        text: str,
        name: str = "",
        trigger_change_event: bool = False,
    ) -> None:
        """Wait for element, clear safely, type text, optionally trigger change.

        Args:
            locator: Element locator.
            text: Text to type.
            name: Element name for logging.
            trigger_change_event: If ``True``, sends Tab key after typing to
                                  trigger ``change`` events in AJAX-heavy apps.
        """
        el = self.wait_for_visible(locator)
        # Clear via triple-click select-all then delete (more reliable than .clear())
        el.click()
        el.send_keys(Keys.CONTROL + "a")
        el.send_keys(Keys.DELETE)
        el.send_keys(text)
        if trigger_change_event:
            el.send_keys(Keys.TAB)

    def select_dropdown(
        self,
        locator: LocatorDefinition,
        by: str,
        value: str,
        name: str = "",
    ) -> None:
        """Select a ``<select>`` option.

        Args:
            locator: Select element locator.
            by: One of ``'text'``, ``'value'``, or ``'index'``.
            value: The option text, value, or index string.
            name: Element name for logging.
        """
        el = self.wait_for_visible(locator)
        sel = Select(el)
        if by == "text":
            sel.select_by_visible_text(value)
        elif by == "value":
            sel.select_by_value(value)
        elif by == "index":
            sel.select_by_index(int(value))
        else:
            raise ElementActionError(f"Unknown select_by '{by}'", element_name=name)

    def check(self, locator: LocatorDefinition, name: str = "") -> None:
        """Check a checkbox if not already checked."""
        el = self.wait_for_visible(locator)
        if not el.is_selected():
            el.click()

    def uncheck(self, locator: LocatorDefinition, name: str = "") -> None:
        """Uncheck a checkbox if currently checked."""
        el = self.wait_for_visible(locator)
        if el.is_selected():
            el.click()

    def select_radio(self, locator: LocatorDefinition, name: str = "") -> None:
        """Select a radio button if not already selected."""
        el = self.wait_for_visible(locator)
        if not el.is_selected():
            el.click()

    def open_new_window(self, type_hint: str = "window") -> None:
        """Open a new browser window or tab and switch focus to it.

        Args:
            type_hint: 'window' for a new OS window, 'tab' for a new tab.
                       Passed directly to driver.switch_to.new_window().
        """
        self._driver.switch_to.new_window(type_hint)

    def switch_to_latest_window(self, timeout: int = 10) -> None:
        """Wait for a new window to appear and switch focus to it.

        Use this after an action (e.g. clicking a link with target="_blank")
        that opens a new window asynchronously. Snapshots handles before
        waiting, uses EC.new_window_is_opened to avoid polling with sleep,
        then switches to the new handle identified by set difference.

        Args:
            timeout: Seconds to wait for the new window to appear.
        """
        from selenium.webdriver.support import expected_conditions as EC

        old_handles = set(self._driver.window_handles)
        self._wm.wait_for(
            EC.new_window_is_opened(list(old_handles)),
            "new window to appear",
            timeout=timeout,
        )
        new_handles = set(self._driver.window_handles) - old_handles
        if not new_handles:
            raise ElementActionError(
                "No new window handle found after waiting",
                element_name="switch_to_latest_window",
            )
        new_handle = new_handles.pop()
        self._driver.switch_to.window(new_handle)

    def scroll_into_view(self, element: WebElement) -> None:
        """Scroll the element into the viewport via JavaScript."""
        self._driver.execute_script(
            "arguments[0].scrollIntoView({behavior:'smooth',block:'center'});",
            element,
        )

    def take_screenshot(self, name: str) -> Optional[str]:
        """Take a screenshot and return the saved file path."""
        return self._screenshots.capture(self._driver, name)

    # ------------------------------------------------------------------
    # Stale element protection
    # ------------------------------------------------------------------

    def retry_on_stale(
        self,
        action_fn: Callable[[], T],
        retries: int = DEFAULT_STALE_RETRY_COUNT,
    ) -> T:
        """Execute ``action_fn`` and retry on :class:`StaleElementReferenceException`.

        Args:
            action_fn: Zero-argument callable that may raise ``StaleElementReferenceException``.
            retries: Maximum number of retry attempts.

        Returns:
            The return value of ``action_fn``.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                return action_fn()
            except StaleElementReferenceException as exc:
                last_exc = exc
                logger.debug("StaleElementReferenceException on attempt %d/%d", attempt + 1, retries)
        raise ElementActionError(
            f"Element stale after {retries} retries: {last_exc}"
        )
