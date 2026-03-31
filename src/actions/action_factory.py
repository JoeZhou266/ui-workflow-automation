from __future__ import annotations

from typing import Optional, Any

from src.actions.element_actions import ElementActions
from src.actions.value_resolver import ValueResolver
from src.core.exceptions import ElementActionError
from src.core.logger import get_logger
from src.models.workflow_models import ElementDefinition
from src.ui.base_page import BasePage
from src.waits.wait_manager import WaitManager

logger = get_logger("action_factory")

_resolver = ValueResolver()


class ActionFactory:
    """Orchestrates the full pre_wait → action → post_wait cycle for one element.

    This is the main entry point called by the workflow engine for each element.
    """

    def __init__(self, page: BasePage, wait_manager: WaitManager) -> None:
        self._executor = ElementActions(page, wait_manager)
        self._wm = wait_manager

    def run(self, element: ElementDefinition) -> None:
        """Run the complete action sequence for a single element.

        Sequence:
        1. ``pre_wait`` — wait before interacting (e.g. wait for options to load)
        2. Execute the action
        3. ``post_wait`` — wait for downstream state change (e.g. next page visible)

        Args:
            element: The element definition from JSON.

        Raises:
            ElementActionError: On interaction or assertion failure.
        """
        resolved_value = _resolver.resolve(element.value)

        # 1. Pre-wait
        if element.pre_wait:
            logger.debug("[%s] Executing pre_wait: %s", element.name, element.pre_wait.condition.value)
            self._wm.wait_for_condition(element.pre_wait, element_name=element.name)

        # 2. Action (with optional retry on retryable elements)
        if element.retryable and element.retry_count > 0:
            self._execute_with_retry(element, resolved_value)
        else:
            self._executor.execute(element, resolved_value)

        # 3. Post-wait
        if element.post_wait:
            logger.debug("[%s] Executing post_wait: %s", element.name, element.post_wait.condition.value)
            self._wm.wait_for_condition(element.post_wait, element_name=element.name)

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
