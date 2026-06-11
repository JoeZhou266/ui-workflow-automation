from __future__ import annotations

import time
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from src.actions.action_factory import ActionFactory
from src.actions.value_resolver import resolve_dynamic_value
from src.core.enums import FailurePhase
from src.core.exceptions import ElementActionError, PageLoadError, SkipElementSignal, WaitTimeoutError
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
        self._params: dict = {
            p.name: resolve_dynamic_value(p.value)
            for p in (self._definition.parameters or [])
        }

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
            if element.index_range is None:
                # Single-element behavior, unchanged (no-regression).
                self._run_element(element, dyn_section, ctx.at_element(element.name))
            else:
                # index_range loop expansion: one declared element -> N per-index runs.
                start, end = element.index_range
                locator_value = element.locator.value if element.locator else None
                # Warn (do not raise) when ${index} is set but appears nowhere it can take
                # effect — every iteration would otherwise target the same element (Pitfall 4).
                if "${index}" not in element.name and (
                    locator_value is None or "${index}" not in locator_value
                ):
                    logger.warning(
                        "[Group] Element '%s' has index_range=%s but no '${index}' token in "
                        "name or locator.value — every iteration targets the same element.",
                        element.name, element.index_range,
                    )
                for i in range(start, end + 1):
                    # NEVER mutate self._params (Pitfall 1) — build a per-iteration copy.
                    merged_params = {**self._params, "index": str(i)}
                    # Substitute ${index} in name (D-04) and locator.value (D-03/D-03b) at the
                    # engine site so the concrete element carries resolved values. model_copy
                    # does not re-run validators (Pitfall 3) — intentional.
                    concrete_name = element.name.replace("${index}", str(i))
                    update: dict = {"name": concrete_name}
                    if locator_value is not None and "${index}" in locator_value:
                        update["locator"] = element.locator.model_copy(
                            update={"value": locator_value.replace("${index}", str(i))}
                        )
                    # WR-03: substitute ${index} inside element.value at the engine site so it
                    # resolves consistently with name/locator (substring replace). Without this,
                    # an embedded token like "row_${index}_amount" would NOT match the anchored
                    # _PLACEHOLDER_PATTERN in resolve_dynamic_value and be typed verbatim. Only
                    # string values are touched; non-string values (None, numbers) pass through.
                    if isinstance(element.value, str) and "${index}" in element.value:
                        update["value"] = element.value.replace("${index}", str(i))
                    concrete_elem = element.model_copy(update=update)
                    # Aside from any per-index ${index} expansion above, the same value applies
                    # to all indices (D-05); a future phase may index a per-index value list
                    # (D-06 — additive, not implemented now).
                    logger.info("[Group] %s (index=%d)", concrete_name, i)
                    self._run_element(
                        concrete_elem, dyn_section, ctx.at_element(concrete_name),
                        params_override=merged_params,
                    )

    def _run_element(
        self,
        element: ElementDefinition,
        section: DynamicSection,
        ctx: ExecutionContext,
        params_override: dict | None = None,
    ) -> None:
        logger.info(
            "[Element] %s | action=%s type=%s",
            element.name, element.action.value, element.type.value,
        )
        # params_override carries the per-index merged params for loop expansion;
        # default None keeps all existing callers backward-compatible (no-regression).
        params = params_override if params_override is not None else self._params
        factory = ActionFactory(section, self._wm, params=params)
        start_ms = time.monotonic()

        try:
            factory.run(element)
            duration_ms = (time.monotonic() - start_ms) * 1000
            self._collector.record_pass(ctx, element.action, duration_ms=duration_ms)

        except SkipElementSignal as exc:
            self._collector.record_skip(
                ctx, element.action, reason=str(exc)
            )

        except WaitTimeoutError as exc:
            duration_ms = (time.monotonic() - start_ms) * 1000
            screenshot = self._take_screenshot(f"wait_timeout_{element.name}")
            phase = self._infer_failure_phase(exc)
            self._collector.record_fail(
                ctx, element.action, str(exc),
                failure_phase=phase,
                screenshot_path=screenshot,
                duration_ms=duration_ms,
            )

        except ElementActionError as exc:
            duration_ms = (time.monotonic() - start_ms) * 1000
            screenshot = self._take_screenshot(f"action_error_{element.name}")
            self._collector.record_fail(
                ctx, element.action, str(exc),
                failure_phase=FailurePhase.ACTION,
                screenshot_path=screenshot,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start_ms) * 1000
            logger.exception("[Element] Unexpected error for '%s'", element.name)
            screenshot = self._take_screenshot(f"unexpected_error_{element.name}")
            self._collector.record_fail(
                ctx, element.action, f"Unexpected: {exc}",
                failure_phase=FailurePhase.ACTION,
                screenshot_path=screenshot,
                duration_ms=duration_ms,
            )

    def _take_screenshot(self, name: str) -> Optional[str]:
        """Capture a screenshot, coercing the result to ``Optional[str]``.

        ``BasePage.take_screenshot`` returns a path string or ``None`` in production,
        which ``StepResult.screenshot_path`` accepts directly. This wrapper guards the
        failure branches so a non-str return (e.g. a mocked page in unit tests) becomes
        ``None`` rather than failing ``StepResult`` validation.
        """
        path = self._page.take_screenshot(name)
        return path if isinstance(path, str) else None

    @staticmethod
    def _infer_failure_phase(exc: WaitTimeoutError) -> FailurePhase:
        msg = str(exc).lower()
        # Match only explicit phase labels to avoid false positives from condition names
        # (e.g. "present" contains "pre", "post_something" could match "post").
        if "pre_wait" in msg:
            return FailurePhase.PRE_WAIT
        if "post_wait" in msg:
            return FailurePhase.POST_WAIT
        return FailurePhase.ACTION
