from __future__ import annotations

from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from src.core.exceptions import PageLoadError
from src.core.exceptions import WaitTimeoutError
from src.core.logger import get_logger
from src.locators.locator_resolver import LocatorResolver
from src.models.workflow_models import LoadCriteria
from src.waits.wait_manager import WaitManager

logger = get_logger("page_readiness")


class PageReadinessChecker:
    """Evaluates whether a page has fully loaded based on :class:`LoadCriteria`.

    Combines:
    - ``document.readyState == 'complete'`` when ``require_document_ready``
    - jQuery/AJAX idle when ``require_ajax_idle``
    - Spinner / overlay disappearance
    - The configured locator/condition
    """

    def __init__(self, driver: WebDriver, wait_manager: WaitManager) -> None:
        self._driver = driver
        self._wm = wait_manager

    def wait_for_page_ready(
        self,
        criteria: Optional[LoadCriteria],
        page_name: str = "",
        tab_name: str = "",
    ) -> None:
        """Block until the page satisfies its load criteria.

        Args:
            criteria: The ``load_criteria`` from the page definition.
                      If ``None``, only a basic document-ready check is performed.
            page_name: For error context only.
            tab_name: For error context only.

        Raises:
            PageLoadError: If any condition times out.
        """
        ctx = f"{tab_name} > {page_name}" if tab_name else page_name

        try:
            if criteria is None:
                logger.debug("No load_criteria for %s — skipping page readiness check", ctx)
                return

            timeout = criteria.timeout

            if criteria.require_document_ready:
                logger.debug("[%s] Waiting for document.readyState", ctx)
                self._wm.wait_document_ready(timeout=timeout)

            if criteria.require_ajax_idle:
                logger.debug("[%s] Waiting for AJAX idle", ctx)
                self._wm.wait_ajax_idle(timeout=timeout)

            if criteria.spinner_locator:
                logger.debug("[%s] Waiting for spinner to disappear", ctx)
                loc = LocatorResolver.resolve(criteria.spinner_locator)
                try:
                    self._wm.wait_invisible(loc, timeout=timeout)
                except WaitTimeoutError:
                    logger.debug("[%s] Spinner did not disappear — continuing", ctx)

            if criteria.overlay_locator:
                logger.debug("[%s] Waiting for overlay to disappear", ctx)
                loc = LocatorResolver.resolve(criteria.overlay_locator)
                try:
                    self._wm.wait_invisible(loc, timeout=timeout)
                except WaitTimeoutError:
                    logger.debug("[%s] Overlay did not disappear — continuing", ctx)

            if criteria.locator and criteria.condition:
                from src.models.workflow_models import WaitConditionDefinition
                wait_def = WaitConditionDefinition(
                    condition=criteria.condition,
                    timeout=timeout,
                    locator=criteria.locator,
                    text_expected=criteria.text_expected,
                    attribute_name=criteria.attribute_name,
                    attribute_value=criteria.attribute_value,
                    minimum_count=criteria.minimum_count,
                )
                logger.debug(
                    "[%s] Waiting for condition '%s' on locator %s=%s",
                    ctx, criteria.condition.value,
                    criteria.locator.by, criteria.locator.value,
                )
                self._wm.wait_for_condition(wait_def, element_name=page_name)

        except WaitTimeoutError as exc:
            raise PageLoadError(
                str(exc), page_name=page_name, tab_name=tab_name
            ) from exc
