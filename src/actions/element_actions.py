from __future__ import annotations

from typing import Any, Optional

from src.core.enums import ActionType, ElementType
from src.core.exceptions import ElementActionError
from src.core.logger import get_logger
from src.models.workflow_models import AssertionDefinition, ElementDefinition
from src.ui.base_page import BasePage
from src.waits.wait_manager import WaitManager

logger = get_logger("element_actions")


class ElementActions:
    """Executes individual element interactions via :class:`BasePage` helpers.

    This is the generic action engine — it dispatches based on
    ``element.action`` and ``element.type``, delegating all Selenium calls
    to the :class:`BasePage` interaction layer.
    """

    def __init__(self, page: BasePage, wait_manager: WaitManager) -> None:
        self._page = page
        self._wm = wait_manager

    def execute(self, element: ElementDefinition, value: Optional[Any] = None) -> None:
        """Execute the configured action for ``element``.

        Args:
            element: The element definition from JSON.
            value: The resolved value (may differ from ``element.value`` after
                   variable substitution).

        Raises:
            ElementActionError: On interaction failure.
        """
        action = element.action
        logger.debug(
            "Executing action=%s type=%s name='%s'",
            action.value, element.type.value, element.name,
        )

        try:
            if action == ActionType.NOOP:
                return

            if action == ActionType.ASSERT_ONLY:
                self._run_assertions(element)
                return

            if action == ActionType.INPUT:
                self._do_input(element, value)

            elif action == ActionType.CLICK:
                self._page.safe_click(element.locator, element.name)

            elif action == ActionType.SELECT_BY_TEXT:
                self._page.select_dropdown(element.locator, "text", str(value), element.name)

            elif action == ActionType.SELECT_BY_VALUE:
                self._page.select_dropdown(element.locator, "value", str(value), element.name)

            elif action == ActionType.SELECT_BY_INDEX:
                self._page.select_dropdown(element.locator, "index", str(value), element.name)

            elif action == ActionType.CHECK:
                self._page.check(element.locator, element.name)

            elif action == ActionType.UNCHECK:
                self._page.uncheck(element.locator, element.name)

            elif action == ActionType.SELECT_RADIO:
                self._page.select_radio(
                    element.locator, element.name, str(value) if value is not None else ""
                )

            elif action == ActionType.UPLOAD:
                self._do_upload(element, value)

            elif action == ActionType.SWITCH_TO_NEW_WINDOW:
                # Opens a blank OS window programmatically; element.locator is not used.
                self._page.open_new_window("window")

            elif action == ActionType.SWITCH_TO_NEW_TAB:
                # Opens a blank tab programmatically; element.locator is not used.
                self._page.open_new_window("tab")

            elif action == ActionType.SWITCH_TO_LATEST_WINDOW:
                self._page.switch_to_latest_window()

            else:
                raise ElementActionError(
                    f"Unhandled action '{action.value}'", element_name=element.name
                )

            # Run any post-action assertions
            if element.assertions:
                self._run_assertions(element)

        except ElementActionError:
            raise
        except Exception as exc:
            raise ElementActionError(
                str(exc), element_name=element.name, action=action.value
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _do_input(self, element: ElementDefinition, value: Optional[Any]) -> None:
        str_value = str(value) if value is not None else ""
        trigger_change = bool(
            element.options and element.options.get("trigger_change_event")
        )
        self._page.clear_and_type(
            element.locator,
            str_value,
            element.name,
            trigger_change_event=trigger_change,
        )

    def _do_upload(self, element: ElementDefinition, value: Optional[Any]) -> None:
        if value is None:
            raise ElementActionError(
                "No file path provided for upload", element_name=element.name
            )
        # For file inputs, send_keys with the file path directly (no click needed)
        el = self._page.wait_for_present(element.locator)
        el.send_keys(str(value))

    def _run_assertions(self, element: ElementDefinition) -> None:
        if not element.assertions:
            return
        for assertion in element.assertions:
            self._assert(assertion, element.name)

    def _assert(self, assertion: AssertionDefinition, element_name: str) -> None:
        from src.core.enums import WaitConditionType
        from src.models.workflow_models import WaitConditionDefinition

        wait_def = WaitConditionDefinition(
            condition=assertion.condition,
            timeout=assertion.timeout,
            locator=assertion.locator,
            text_expected=assertion.text_expected,
            attribute_name=assertion.attribute_name,
            attribute_value=assertion.attribute_value,
        )
        try:
            self._wm.wait_for_condition(wait_def, element_name=element_name)
        except Exception as exc:
            raise ElementActionError(
                f"Assertion failed: {exc}",
                element_name=element_name,
                action="assertion",
            ) from exc
