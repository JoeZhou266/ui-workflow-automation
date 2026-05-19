"""Unit tests for ElementActions and ActionFactory using mocked Selenium."""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest

from src.actions.element_actions import ElementActions
from src.actions.action_factory import ActionFactory
from src.actions.value_resolver import ValueResolver
from src.core.enums import ActionType, ElementType
from src.models.workflow_models import ElementDefinition, LocatorDefinition


def _make_locator(by: str = "id", value: str = "el") -> LocatorDefinition:
    return LocatorDefinition(by=by, value=value)


def _make_element(
    name: str = "El",
    etype: ElementType = ElementType.BUTTON,
    action: ActionType = ActionType.CLICK,
    value=None,
    **kwargs,
) -> ElementDefinition:
    return ElementDefinition(
        name=name,
        type=etype,
        action=action,
        locator=_make_locator(),
        value=value,
        **kwargs,
    )


@pytest.fixture
def mock_page():
    page = MagicMock()
    page.wait_for_visible.return_value = MagicMock()
    page.wait_for_present.return_value = MagicMock()
    page.wait_for_clickable.return_value = MagicMock()
    return page


@pytest.fixture
def mock_wm():
    return MagicMock()


@pytest.fixture
def executor(mock_page, mock_wm):
    return ElementActions(mock_page, mock_wm)


class TestElementActions:
    def test_click_action(self, executor, mock_page):
        el = _make_element(action=ActionType.CLICK)
        executor.execute(el)
        mock_page.safe_click.assert_called_once_with(el.locator, el.name)

    def test_input_action(self, executor, mock_page):
        el = _make_element(
            etype=ElementType.TEXT,
            action=ActionType.INPUT,
            value="hello",
        )
        executor.execute(el, value="hello")
        mock_page.clear_and_type.assert_called_once()
        args = mock_page.clear_and_type.call_args
        assert args[0][1] == "hello"

    def test_select_by_text(self, executor, mock_page):
        el = _make_element(
            etype=ElementType.SELECT,
            action=ActionType.SELECT_BY_TEXT,
            value="Option A",
        )
        executor.execute(el, value="Option A")
        mock_page.select_dropdown.assert_called_once_with(
            el.locator, "text", "Option A", el.name
        )

    def test_select_by_value(self, executor, mock_page):
        el = _make_element(
            etype=ElementType.SELECT,
            action=ActionType.SELECT_BY_VALUE,
            value="opt_a",
        )
        executor.execute(el, value="opt_a")
        mock_page.select_dropdown.assert_called_once_with(
            el.locator, "value", "opt_a", el.name
        )

    def test_select_by_index(self, executor, mock_page):
        el = _make_element(
            etype=ElementType.SELECT,
            action=ActionType.SELECT_BY_INDEX,
            value="2",
        )
        executor.execute(el, value="2")
        mock_page.select_dropdown.assert_called_once_with(
            el.locator, "index", "2", el.name
        )

    def test_check_action(self, executor, mock_page):
        el = _make_element(etype=ElementType.CHECKBOX, action=ActionType.CHECK)
        executor.execute(el)
        mock_page.check.assert_called_once_with(el.locator, el.name)

    def test_uncheck_action(self, executor, mock_page):
        el = _make_element(etype=ElementType.CHECKBOX, action=ActionType.UNCHECK)
        executor.execute(el)
        mock_page.uncheck.assert_called_once_with(el.locator, el.name)

    def test_noop_action_does_nothing(self, executor, mock_page):
        el = _make_element(action=ActionType.NOOP)
        executor.execute(el)
        mock_page.safe_click.assert_not_called()
        mock_page.clear_and_type.assert_not_called()

    def test_upload_action(self, executor, mock_page):
        el = _make_element(
            etype=ElementType.FILE,
            action=ActionType.UPLOAD,
            value="/path/to/file.pdf",
        )
        mock_el = MagicMock()
        mock_page.wait_for_present.return_value = mock_el
        executor.execute(el, value="/path/to/file.pdf")
        mock_el.send_keys.assert_called_once_with("/path/to/file.pdf")

    def test_upload_without_value_raises(self, executor):
        from src.core.exceptions import ElementActionError
        el = _make_element(etype=ElementType.FILE, action=ActionType.UPLOAD)
        with pytest.raises(ElementActionError, match="No file path"):
            executor.execute(el, value=None)

    def test_select_radio_action(self, executor, mock_page):
        el = _make_element(etype=ElementType.RADIO, action=ActionType.SELECT_RADIO)
        executor.execute(el)
        mock_page.select_radio.assert_called_once_with(el.locator, el.name, "")

    def test_select_radio_already_selected(self):
        """BasePage.select_radio must not click an already-selected radio."""
        from src.ui.base_page import BasePage

        # Case 1: already selected -> no click
        already_selected_el = MagicMock()
        already_selected_el.is_selected.return_value = True
        page = MagicMock(spec=BasePage)
        page.wait_for_visible.return_value = already_selected_el
        BasePage.select_radio(page, _make_locator(), "radio-1")
        already_selected_el.click.assert_not_called()

        # Case 2: not selected -> exactly one click
        not_selected_el = MagicMock()
        not_selected_el.is_selected.return_value = False
        page2 = MagicMock(spec=BasePage)
        page2.wait_for_visible.return_value = not_selected_el
        BasePage.select_radio(page2, _make_locator(), "radio-2")
        not_selected_el.click.assert_called_once()

    def test_number_input_action(self, executor, mock_page):
        el = _make_element(
            etype=ElementType.NUMBER,
            action=ActionType.INPUT,
            value="42",
        )
        executor.execute(el, value="42")
        mock_page.clear_and_type.assert_called_once()
        args = mock_page.clear_and_type.call_args
        assert args[0][1] == "42"

    def test_email_input_action(self, executor, mock_page):
        el = _make_element(
            etype=ElementType.EMAIL,
            action=ActionType.INPUT,
            value="user@example.com",
        )
        executor.execute(el, value="user@example.com")
        mock_page.clear_and_type.assert_called_once()
        args = mock_page.clear_and_type.call_args
        assert args[0][1] == "user@example.com"

    def test_switch_to_new_window_action(self, executor, mock_page):
        el = _make_element(etype=ElementType.BUTTON, action=ActionType.SWITCH_TO_NEW_WINDOW)
        executor.execute(el)
        mock_page.open_new_window.assert_called_once_with("window")

    def test_switch_to_new_tab_action(self, executor, mock_page):
        el = _make_element(etype=ElementType.BUTTON, action=ActionType.SWITCH_TO_NEW_TAB)
        executor.execute(el)
        mock_page.open_new_window.assert_called_once_with("tab")

    def test_switch_to_latest_window_action(self, executor, mock_page):
        el = _make_element(etype=ElementType.BUTTON, action=ActionType.SWITCH_TO_LATEST_WINDOW)
        executor.execute(el)
        mock_page.switch_to_latest_window.assert_called_once()


class TestActionFactory:
    def test_pre_wait_called_before_action(self, mock_page, mock_wm):
        from src.models.workflow_models import WaitConditionDefinition
        from src.core.enums import WaitConditionType

        pre_wait = WaitConditionDefinition(
            condition=WaitConditionType.VISIBLE,
            timeout=5,
            locator=_make_locator(),
        )
        el = _make_element(action=ActionType.CLICK, pre_wait=pre_wait)
        factory = ActionFactory(mock_page, mock_wm)

        call_order = []
        mock_wm.wait_for_condition.side_effect = lambda *a, **kw: call_order.append("wait")
        mock_page.safe_click.side_effect = lambda *a, **kw: call_order.append("click")

        factory.run(el)
        assert call_order[0] == "wait"
        assert call_order[1] == "click"

    def test_post_wait_called_after_action(self, mock_page, mock_wm):
        from src.models.workflow_models import WaitConditionDefinition
        from src.core.enums import WaitConditionType

        post_wait = WaitConditionDefinition(
            condition=WaitConditionType.VISIBLE,
            timeout=5,
            locator=_make_locator(),
        )
        el = _make_element(action=ActionType.CLICK, post_wait=post_wait)
        factory = ActionFactory(mock_page, mock_wm)

        call_order = []
        mock_page.safe_click.side_effect = lambda *a, **kw: call_order.append("click")
        mock_wm.wait_for_condition.side_effect = lambda *a, **kw: call_order.append("wait")

        factory.run(el)
        assert call_order[0] == "click"
        assert call_order[1] == "wait"

    def test_retry_on_retryable_element(self, mock_page, mock_wm):
        from src.core.exceptions import ElementActionError

        el = _make_element(action=ActionType.CLICK, retryable=True, retry_count=2)
        factory = ActionFactory(mock_page, mock_wm)

        mock_page.safe_click.side_effect = [
            ElementActionError("fail1"),
            ElementActionError("fail2"),
            None,  # third attempt succeeds
        ]
        factory.run(el)
        assert mock_page.safe_click.call_count == 3

    def test_exhausted_retries_raises(self, mock_page, mock_wm):
        from src.core.exceptions import ElementActionError

        el = _make_element(action=ActionType.CLICK, retryable=True, retry_count=1)
        factory = ActionFactory(mock_page, mock_wm)
        mock_page.safe_click.side_effect = ElementActionError("always fails")

        with pytest.raises(ElementActionError):
            factory.run(el)


class TestValueResolver:
    def test_none_returns_none(self):
        r = ValueResolver()
        assert r.resolve(None) is None

    def test_string_passthrough(self):
        r = ValueResolver()
        assert r.resolve("hello") == "hello"

    def test_int_passthrough(self):
        r = ValueResolver()
        assert r.resolve(42) == 42

    def test_list_passthrough(self):
        r = ValueResolver()
        assert r.resolve(["a", "b"]) == ["a", "b"]
