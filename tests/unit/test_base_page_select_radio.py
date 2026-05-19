"""Unit tests for BasePage.select_radio() using mocked Selenium."""
from __future__ import annotations

from unittest.mock import MagicMock, call
import pytest

from src.models.workflow_models import LocatorDefinition


def _make_locator(by: str = "id", value: str = "radio-el") -> LocatorDefinition:
    return LocatorDefinition(by=by, value=value)


def _make_page():
    """Return a minimal mock that exercises the real select_radio implementation."""
    from src.ui.base_page import BasePage
    from unittest.mock import patch

    driver = MagicMock()
    wm = MagicMock()
    screenshots = MagicMock()
    config = MagicMock()
    config.explicit_wait = 20

    with patch("src.ui.base_page.WaitManager"):
        page = BasePage.__new__(BasePage)
        page._driver = driver
        page._wm = wm
        page._screenshots = screenshots
        return page


class TestSelectRadio:
    def test_happy_path_clicks_when_not_selected(self):
        """When element is not selected, select_radio must call el.click() once."""
        page = _make_page()
        mock_el = MagicMock()
        mock_el.is_selected.return_value = False
        page.wait_for_visible = MagicMock(return_value=mock_el)

        locator = _make_locator()
        page.select_radio(locator)

        page.wait_for_visible.assert_called_once_with(locator)
        mock_el.click.assert_called_once()

    def test_idempotent_no_click_when_already_selected(self):
        """When element is already selected, select_radio must NOT call el.click()."""
        page = _make_page()
        mock_el = MagicMock()
        mock_el.is_selected.return_value = True
        page.wait_for_visible = MagicMock(return_value=mock_el)

        locator = _make_locator()
        page.select_radio(locator)

        page.wait_for_visible.assert_called_once_with(locator)
        mock_el.click.assert_not_called()

    def test_calls_wait_for_visible_before_dom_interaction(self):
        """select_radio must call wait_for_visible(locator) before any DOM interaction."""
        page = _make_page()
        call_order = []

        mock_el = MagicMock()
        mock_el.is_selected.side_effect = lambda: call_order.append("is_selected") or False
        mock_el.click.side_effect = lambda: call_order.append("click")

        def mock_wait_for_visible(loc):
            call_order.append("wait_for_visible")
            return mock_el

        page.wait_for_visible = mock_wait_for_visible

        page.select_radio(_make_locator())

        assert call_order[0] == "wait_for_visible", (
            f"wait_for_visible must be first; got order={call_order}"
        )

    def test_signature_name_optional_returns_none(self):
        """select_radio(locator, name='') -> None: name is optional, return is None."""
        page = _make_page()
        mock_el = MagicMock()
        mock_el.is_selected.return_value = False
        page.wait_for_visible = MagicMock(return_value=mock_el)

        locator = _make_locator()
        # Call with explicit name kwarg — must not raise
        result = page.select_radio(locator, name="My Radio")

        assert result is None

    def test_name_and_value_builds_css_selector(self):
        """When locator.by=='name' and value is set, wait_for_visible receives a
        CSS selector locator: input[type="radio"][name="..."][value="..."]."""
        from src.models.workflow_models import LocatorDefinition

        page = _make_page()
        mock_el = MagicMock()
        mock_el.is_selected.return_value = False
        captured = {}

        def capture_locator(loc):
            captured["loc"] = loc
            return mock_el

        page.wait_for_visible = capture_locator

        locator = _make_locator(by="name", value="gender")
        page.select_radio(locator, value="female")

        assert captured["loc"].by == "css_selector"
        assert 'name="gender"' in captured["loc"].value
        assert 'value="female"' in captured["loc"].value
        assert 'input[type="radio"]' in captured["loc"].value
        mock_el.click.assert_called_once()

    def test_name_locator_without_value_uses_locator_directly(self):
        """When locator.by=='name' but value is empty, uses the original locator."""
        page = _make_page()
        mock_el = MagicMock()
        mock_el.is_selected.return_value = False
        page.wait_for_visible = MagicMock(return_value=mock_el)

        locator = _make_locator(by="name", value="gender")
        page.select_radio(locator)

        page.wait_for_visible.assert_called_once_with(locator)

    def test_non_name_locator_with_value_uses_locator_directly(self):
        """When locator.by!='name', value param is ignored and original locator is used."""
        page = _make_page()
        mock_el = MagicMock()
        mock_el.is_selected.return_value = False
        page.wait_for_visible = MagicMock(return_value=mock_el)

        locator = _make_locator(by="id", value="radio-female")
        page.select_radio(locator, value="female")

        page.wait_for_visible.assert_called_once_with(locator)
