from __future__ import annotations

from typing import Callable, Optional, Tuple

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.core.constants import DEFAULT_EXPLICIT_WAIT_TIMEOUT, DEFAULT_POLL_FREQUENCY_MS
from src.core.enums import WaitConditionType
from src.core.exceptions import WaitTimeoutError
from src.core.logger import get_logger
from src.models.workflow_models import LocatorDefinition, WaitConditionDefinition
from src.locators.locator_resolver import LocatorResolver
from src.waits import expected_states as es
from src.waits.ajax_monitor import AjaxMonitor

logger = get_logger("wait_manager")


class WaitManager:
    """Single entry point for all explicit waits.

    Wraps :class:`WebDriverWait`, logs what it is waiting for, and raises
    :class:`WaitTimeoutError` with context on timeout instead of the raw
    Selenium ``TimeoutException``.
    """

    def __init__(
        self,
        driver: WebDriver,
        default_timeout: int = DEFAULT_EXPLICIT_WAIT_TIMEOUT,
        default_poll_ms: int = DEFAULT_POLL_FREQUENCY_MS,
    ) -> None:
        self._driver = driver
        self._default_timeout = default_timeout
        self._default_poll_ms = default_poll_ms
        self._ajax = AjaxMonitor(driver)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def wait_for(
        self,
        condition: Callable,
        description: str,
        timeout: Optional[int] = None,
        poll_ms: Optional[int] = None,
    ) -> object:
        """Poll until ``condition(driver)`` returns truthy or timeout elapses.

        Args:
            condition: Any callable accepted by :class:`WebDriverWait`.
            description: Human-readable description logged during the wait.
            timeout: Override default timeout (seconds).
            poll_ms: Override default poll frequency (milliseconds).

        Returns:
            The truthy return value of the condition.

        Raises:
            WaitTimeoutError: On timeout.
        """
        t = timeout if timeout is not None else self._default_timeout
        p = (poll_ms if poll_ms is not None else self._default_poll_ms) / 1000.0

        logger.debug("Waiting (up to %ds): %s", t, description)
        wait = WebDriverWait(self._driver, t, poll_frequency=p)
        try:
            result = wait.until(condition)
            logger.debug("Wait satisfied: %s", description)
            return result
        except TimeoutException as exc:
            raise WaitTimeoutError(condition=description, timeout=t) from exc

    def wait_for_condition(
        self,
        condition_def: WaitConditionDefinition,
        element_name: str = "",
    ) -> None:
        """Resolve and execute a :class:`WaitConditionDefinition`.

        This is the primary method called by the workflow engine for
        ``pre_wait`` and ``post_wait`` definitions.
        """
        ctype = condition_def.condition
        t = condition_def.timeout
        p = condition_def.poll_frequency_ms

        # Optional document/AJAX readiness checks first
        if condition_def.require_document_ready:
            self.wait_for(
                self._ajax.document_ready_condition(),
                "document.readyState == complete",
                timeout=t,
                poll_ms=p,
            )
        if condition_def.require_ajax_idle:
            self.wait_for(
                self._ajax.ajax_idle_condition(),
                "AJAX idle",
                timeout=t,
                poll_ms=p,
            )

        # Spinner / overlay gone first (unblock the target element)
        if condition_def.spinner_locator:
            self._wait_gone(condition_def.spinner_locator, "spinner", t, p)
        if condition_def.overlay_locator:
            self._wait_gone(condition_def.overlay_locator, "overlay", t, p)

        # Main wait condition
        locator = condition_def.locator
        loc_tuple: Optional[Tuple[str, str]] = None
        if locator:
            loc_tuple = LocatorResolver.resolve(locator, element_name)

        desc = f"{ctype.value}" + (f" [{element_name}]" if element_name else "")
        self._dispatch(ctype, loc_tuple, condition_def, desc, t, p)

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def wait_visible(self, locator_tuple: Tuple[str, str], timeout: Optional[int] = None) -> object:
        return self.wait_for(
            EC.visibility_of_element_located(locator_tuple),
            f"visible: {locator_tuple}",
            timeout=timeout,
        )

    def wait_clickable(self, locator_tuple: Tuple[str, str], timeout: Optional[int] = None) -> object:
        return self.wait_for(
            EC.element_to_be_clickable(locator_tuple),
            f"clickable: {locator_tuple}",
            timeout=timeout,
        )

    def wait_present(self, locator_tuple: Tuple[str, str], timeout: Optional[int] = None) -> object:
        return self.wait_for(
            EC.presence_of_element_located(locator_tuple),
            f"present: {locator_tuple}",
            timeout=timeout,
        )

    def wait_invisible(self, locator_tuple: Tuple[str, str], timeout: Optional[int] = None) -> None:
        self.wait_for(
            EC.invisibility_of_element_located(locator_tuple),
            f"invisible: {locator_tuple}",
            timeout=timeout,
        )

    def wait_document_ready(self, timeout: Optional[int] = None) -> None:
        self.wait_for(
            self._ajax.document_ready_condition(),
            "document.readyState == complete",
            timeout=timeout,
        )

    def wait_ajax_idle(self, timeout: Optional[int] = None) -> None:
        self.wait_for(
            self._ajax.ajax_idle_condition(),
            "AJAX idle",
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _wait_gone(
        self,
        locator_def: LocatorDefinition,
        label: str,
        timeout: int,
        poll_ms: int,
    ) -> None:
        try:
            loc = LocatorResolver.resolve(locator_def)
            self.wait_for(
                es.element_gone(loc),
                f"{label} gone",
                timeout=timeout,
                poll_ms=poll_ms,
            )
        except WaitTimeoutError:
            logger.debug("%s did not disappear within timeout — continuing", label)

    def _dispatch(
        self,
        ctype: WaitConditionType,
        loc: Optional[Tuple[str, str]],
        cdef: WaitConditionDefinition,
        desc: str,
        timeout: int,
        poll_ms: int,
    ) -> None:
        if ctype == WaitConditionType.VISIBLE:
            if loc:
                self.wait_for(EC.visibility_of_element_located(loc), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.CLICKABLE:
            if loc:
                self.wait_for(EC.element_to_be_clickable(loc), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.PRESENT:
            if loc:
                self.wait_for(EC.presence_of_element_located(loc), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.INVISIBLE:
            if loc:
                self.wait_for(EC.invisibility_of_element_located(loc), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.SELECTED:
            if loc:
                self.wait_for(EC.element_located_to_be_selected(loc), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.URL_CONTAINS:
            if cdef.text_expected:
                self.wait_for(EC.url_contains(cdef.text_expected), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.TEXT_EQUALS:
            if loc and cdef.text_expected is not None:
                self.wait_for(es.element_text_equals(loc, cdef.text_expected), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.TEXT_CONTAINS:
            if loc and cdef.text_expected is not None:
                self.wait_for(es.element_text_contains(loc, cdef.text_expected), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.VALUE_EQUALS:
            if loc and cdef.text_expected is not None:
                self.wait_for(es.element_value_equals(loc, cdef.text_expected), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.ATTRIBUTE_EQUALS:
            if loc and cdef.attribute_name and cdef.attribute_value is not None:
                self.wait_for(es.element_attribute_equals(loc, cdef.attribute_name, cdef.attribute_value), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.ATTRIBUTE_CONTAINS:
            if loc and cdef.attribute_name and cdef.attribute_value is not None:
                self.wait_for(es.element_attribute_contains(loc, cdef.attribute_name, cdef.attribute_value), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.COUNT_GREATER_THAN:
            if loc and cdef.minimum_count is not None:
                self.wait_for(es.element_count_greater_than(loc, cdef.minimum_count), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.OPTIONS_COUNT_GREATER_THAN:
            if loc and cdef.minimum_count is not None:
                self.wait_for(es.options_count_greater_than(loc, cdef.minimum_count), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.DOCUMENT_READY:
            self.wait_for(self._ajax.document_ready_condition(), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.AJAX_IDLE:
            self.wait_for(self._ajax.ajax_idle_condition(), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.SPINNER_GONE:
            if loc:
                self.wait_for(es.element_gone(loc), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.OVERLAY_GONE:
            if loc:
                self.wait_for(es.element_gone(loc), desc, timeout=timeout, poll_ms=poll_ms)
        elif ctype == WaitConditionType.ENABLED:
            if loc:
                self.wait_for(es.element_enabled(loc), desc, timeout=timeout, poll_ms=poll_ms)
        else:
            logger.warning("Unhandled wait condition type: %s", ctype)
