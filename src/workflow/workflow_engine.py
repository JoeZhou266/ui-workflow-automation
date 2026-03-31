from __future__ import annotations

import time
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from src.actions.action_factory import ActionFactory
from src.core.enums import FailurePhase
from src.core.exceptions import ElementActionError, PageLoadError, WaitTimeoutError
from src.core.logger import get_logger
from src.models.element_models import ExecutionSummary
from src.models.workflow_models import (
    ElementDefinition,
    PageDefinition,
    SectionDefinition,
    TabDefinition,
    WorkflowDefinition,
)
from src.ui.base_page import BasePage
from src.ui.pages.dynamic_page import DynamicPage
from src.ui.sections.dynamic_section import DynamicSection
from src.utils.screenshots import ScreenshotManager
from src.waits.wait_manager import WaitManager
from src.workflow.execution_context import ExecutionContext
from src.workflow.navigator import Navigator
from src.workflow.result_collector import ResultCollector

logger = get_logger("workflow_engine")


class WorkflowEngine:
    """Orchestrates the complete workflow: tabs → pages → sections → elements.

    Responsibilities:
    - Load and validate (caller's job, but accepts already-validated model)
    - Navigate to start URL
    - Iterate hierarchy in declared order
    - Wait for page readiness at each page transition
    - Dispatch pre_wait → action → post_wait for each element
    - Collect step results and capture screenshots on failure
    - Return an :class:`ExecutionSummary`
    """

    def __init__(
        self,
        driver: WebDriver,
        definition: WorkflowDefinition,
        base_url: str = "",
        default_wait_timeout: int = 10,
        screenshots_dir: str = "reports/screenshots",
    ) -> None:
        self._driver = driver
        self._definition = definition
        self._screenshots = ScreenshotManager(screenshots_dir)
        self._wm = WaitManager(driver, default_timeout=default_wait_timeout)
        self._page = BasePage(driver, self._wm, self._screenshots)
        self._navigator = Navigator(driver, base_url)
        self._collector = ResultCollector(definition.workflow_name)

    def run(self) -> ExecutionSummary:
        """Execute the full workflow and return the result summary."""
        self._collector.start()
        ctx = ExecutionContext(workflow_name=self._definition.workflow_name)

        logger.info("=== Workflow START: %s ===", self._definition.workflow_name)
        self._navigator.open_start_url(self._definition.start_url)

        for tab in self._definition.ordered_tabs:
            self._run_tab(tab, ctx.at_tab(tab.name))

        self._collector.finish()
        logger.info("=== Workflow END: %s ===", self._definition.workflow_name)
        return self._collector.summary()

    # ------------------------------------------------------------------
    # Hierarchy traversal
    # ------------------------------------------------------------------

    def _run_tab(self, tab: TabDefinition, ctx: ExecutionContext) -> None:
        logger.info("[Tab] %s", tab.name)
        for page in tab.ordered_pages:
            self._run_page(page, ctx.at_page(page.name))

    def _run_page(self, page: PageDefinition, ctx: ExecutionContext) -> None:
        logger.info("[Page] %s", page.name)
        dyn_page = DynamicPage(self._driver, self._wm, page, self._screenshots)

        try:
            dyn_page.ensure_ready(tab_name=ctx.tab_name)
        except PageLoadError as exc:
            screenshot = self._page.take_screenshot(f"page_load_error_{page.name}")
            logger.error("[Page] Load failed for '%s': %s", page.name, exc)
            # Record all elements in this page as failed-skipped
            for section in page.ordered_sections:
                for element in section.elements:
                    elem_ctx = ctx.at_section(section.name).at_element(element.name)
                    self._collector.record_fail(
                        elem_ctx,
                        element.action,
                        str(exc),
                        failure_phase=FailurePhase.PAGE_LOAD,
                        screenshot_path=screenshot,
                    )
            return

        for section in page.ordered_sections:
            self._run_section(section, ctx.at_section(section.name))

    def _run_section(self, section: SectionDefinition, ctx: ExecutionContext) -> None:
        logger.info("[Section] %s", section.name)
        dyn_section = DynamicSection(self._driver, self._wm, section, self._screenshots)

        for element in section.elements:
            self._run_element(element, dyn_section, ctx.at_element(element.name))

    def _run_element(
        self,
        element: ElementDefinition,
        section: DynamicSection,
        ctx: ExecutionContext,
    ) -> None:
        logger.info(
            "[Element] %s | action=%s type=%s",
            element.name, element.action.value, element.type.value,
        )
        factory = ActionFactory(section, self._wm)
        start_ms = time.monotonic()

        try:
            factory.run(element)
            duration_ms = (time.monotonic() - start_ms) * 1000
            self._collector.record_pass(ctx, element.action, duration_ms=duration_ms)

        except WaitTimeoutError as exc:
            duration_ms = (time.monotonic() - start_ms) * 1000
            screenshot = self._page.take_screenshot(f"wait_timeout_{element.name}")
            phase = self._infer_failure_phase(exc)
            self._collector.record_fail(
                ctx, element.action, str(exc),
                failure_phase=phase,
                screenshot_path=screenshot,
                duration_ms=duration_ms,
            )

        except ElementActionError as exc:
            duration_ms = (time.monotonic() - start_ms) * 1000
            screenshot = self._page.take_screenshot(f"action_error_{element.name}")
            self._collector.record_fail(
                ctx, element.action, str(exc),
                failure_phase=FailurePhase.ACTION,
                screenshot_path=screenshot,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start_ms) * 1000
            logger.exception("[Element] Unexpected error for '%s'", element.name)
            screenshot = self._page.take_screenshot(f"unexpected_error_{element.name}")
            self._collector.record_fail(
                ctx, element.action, f"Unexpected: {exc}",
                failure_phase=FailurePhase.ACTION,
                screenshot_path=screenshot,
                duration_ms=duration_ms,
            )

    @staticmethod
    def _infer_failure_phase(exc: WaitTimeoutError) -> FailurePhase:
        msg = str(exc).lower()
        if "pre" in msg or "pre_wait" in msg:
            return FailurePhase.PRE_WAIT
        if "post" in msg or "post_wait" in msg:
            return FailurePhase.POST_WAIT
        return FailurePhase.ACTION
