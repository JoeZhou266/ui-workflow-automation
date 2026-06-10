from __future__ import annotations

from typing import Optional, Any

from src.actions.element_actions import ElementActions
from src.actions.value_resolver import ValueResolver
from src.core.exceptions import ElementActionError, SkipElementSignal
from src.core.logger import get_logger
from src.models.workflow_models import ElementDefinition, LocatorDefinition
from src.ui.base_page import BasePage
from src.waits.wait_manager import WaitManager

logger = get_logger("action_factory")


class ActionFactory:
    """Orchestrates the full pre_wait → action → post_wait cycle for one element.

    This is the main entry point called by the workflow engine for each element.
    """

    def __init__(self, page: BasePage, wait_manager: WaitManager, params: dict | None = None) -> None:
        self._executor = ElementActions(page, wait_manager)
        self._wm = wait_manager
        self._page = page
        self._resolver = ValueResolver(params=params)
        self._params: dict = params or {}

    def _resolve_locator(self, locator: LocatorDefinition) -> LocatorDefinition:
        """Return a :class:`LocatorDefinition` with ``${param}`` tokens expanded.

        Uses the non-anchored :func:`~src.actions.value_resolver.resolve_locator_params`
        for partial/embedded expansion (D-01, D-02). Resolves from
        ``self._params`` only; env config and generators are not consulted (D-04).

        Returns the *same* object when no expansion is needed (zero allocation):
        - The resolved value equals the original (no ``${...}`` tokens present).

        Raises:
            ValueError: If *locator.value* contains an unknown ``${token}``
                (D-05 fail-loud; propagates out of :meth:`run` to the
                workflow engine's exception handler).
        """
        if not isinstance(locator.value, str):
            return locator  # non-string locator values pass through unchanged
        from src.actions.value_resolver import resolve_locator_params
        resolved_value = resolve_locator_params(locator.value, self._params)
        if resolved_value == locator.value:
            return locator  # no tokens — reuse original, zero allocation
        return LocatorDefinition(by=locator.by, value=resolved_value)

    def run(self, element: ElementDefinition) -> None:
        """Run the complete action sequence for a single element.

        Sequence:
        1. Resolve locator params (upstream seam, option b — D-01..D-05)
        2. ``skip_if_not_visible`` probe on resolved locator
        3. ``pre_wait`` — wait before interacting (e.g. wait for options to load)
        4. Execute the action (with resolved locator + element value)
        5. ``post_wait`` — wait for downstream state change (e.g. next page visible)

        Args:
            element: The element definition from JSON.

        Raises:
            ElementActionError: On interaction or assertion failure.
            SkipElementSignal: When skip_if_not_visible=True and element is not visible.
            ValueError: When element.locator.value contains an unknown ${param} token.
        """
        # Resolve locator params BEFORE any probe or action (D-01).
        # ValueError from unknown tokens propagates to WorkflowEngine (D-05).
        resolved_locator = self._resolve_locator(element.locator)
        target = (
            element
            if resolved_locator is element.locator
            else element.model_copy(update={"locator": resolved_locator})
        )

        if target.options and target.options.get("skip_if_not_visible"):
            if not self._page.is_visible(target.locator):
                logger.info(
                    "[%s] Not visible — skipping (skip_if_not_visible=true)", target.name
                )
                raise SkipElementSignal(target.name)

        # element.value anchored path is unchanged (D-03)
        resolved_value = self._resolver.resolve(element.value)

        # 1. Pre-wait
        if target.pre_wait:
            logger.debug("[%s] Executing pre_wait: %s", target.name, target.pre_wait.condition.value)
            self._wm.wait_for_condition(target.pre_wait, element_name=target.name)

        # 2. Action (with optional retry on retryable elements)
        if target.retryable and target.retry_count > 0:
            self._execute_with_retry(target, resolved_value)
        else:
            self._executor.execute(target, resolved_value)

        # 3. Post-wait
        if target.post_wait:
            logger.debug("[%s] Executing post_wait: %s", target.name, target.post_wait.condition.value)
            self._wm.wait_for_condition(target.post_wait, element_name=target.name)

    def _execute_with_retry(
        self, element: ElementDefinition, value: Optional[Any]
    ) -> None:
        last_exc: Optional[Exception] = None
        for attempt in range(element.retry_count + 1):
            try:
                self._executor.execute(element, value)
                return
            except ElementActionError as exc:
                last_exc = exc
                logger.warning(
                    "[%s] Action failed on attempt %d/%d: %s",
                    element.name, attempt + 1, element.retry_count + 1, exc,
                )
        raise ElementActionError(
            f"Action failed after {element.retry_count + 1} attempts: {last_exc}",
            element_name=element.name,
        )
