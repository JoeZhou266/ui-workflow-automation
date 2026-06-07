"""Unit tests for BasePage._select_first_valid_option() and select_dropdown first_valid sentinel."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from src.models.workflow_models import LocatorDefinition
from src.ui.base_page import BasePage
from src.core.exceptions import ElementActionError
from selenium.webdriver.support.select import Select


def _make_locator(by: str = "id", value: str = "sel-el") -> LocatorDefinition:
    return LocatorDefinition(by=by, value=value)


def _make_mock_option(value_attr):
    """Returns a mock <option> element with given get_attribute('value') return."""
    opt = MagicMock()
    opt.get_attribute.side_effect = lambda attr: value_attr if attr == "value" else None
    return opt


def _make_page_with_options(value_attrs):
    """Return a BasePage with wait_for_visible mocked to return a Select-compatible element.

    The mock select element's find_elements returns mock options in DOM order,
    so Select(mock_el).options yields them in the given order.
    """
    driver = MagicMock()
    wm = MagicMock()

    with patch("src.ui.base_page.WaitManager"):
        page = BasePage.__new__(BasePage)
        page._driver = driver
        page._wm = wm
        page._screenshots = MagicMock()

    mock_options = [_make_mock_option(v) for v in value_attrs]
    mock_select_el = MagicMock()
    mock_select_el.tag_name = "select"
    mock_select_el.get_dom_attribute.return_value = None   # not a multiple-select
    mock_select_el.find_elements.return_value = mock_options

    page.wait_for_visible = MagicMock(return_value=mock_select_el)

    return page, mock_options


class TestSelectFirstValid:
    def test_selects_first_non_empty_value_option(self):
        """FV-01: options [None, '', 'real'] — third option's .click() called exactly once."""
        page, opts = _make_page_with_options([None, "", "real"])
        locator = _make_locator()

        page.select_dropdown(locator, "index", "first_valid", "my-select")

        opts[0].click.assert_not_called()
        opts[1].click.assert_not_called()
        opts[2].click.assert_called_once()

    def test_sentinel_case_insensitive(self):
        """FV-02: 'FIRST_VALID' and 'First_Valid' both reach the helper without ValueError."""
        for sentinel in ("FIRST_VALID", "First_Valid"):
            page, opts = _make_page_with_options(["real"])
            locator = _make_locator()

            # Must not raise ValueError (which int("first_valid") would) and must click
            page.select_dropdown(locator, "index", sentinel, "my-select")
            opts[0].click.assert_called_once()

    def test_whitespace_value_skipped(self):
        """FV-03: option with value='   ' is skipped; second option is selected."""
        page, opts = _make_page_with_options(["   ", "real"])
        locator = _make_locator()

        page.select_dropdown(locator, "index", "first_valid", "my-select")

        opts[0].click.assert_not_called()
        opts[1].click.assert_called_once()

    def test_empty_string_value_skipped(self):
        """FV-04: option with value='' is skipped; second option is selected."""
        page, opts = _make_page_with_options(["", "real"])
        locator = _make_locator()

        page.select_dropdown(locator, "index", "first_valid", "my-select")

        opts[0].click.assert_not_called()
        opts[1].click.assert_called_once()

    def test_none_value_attribute_skipped(self):
        """FV-05: option returning None from get_attribute is skipped without AttributeError."""
        page, opts = _make_page_with_options([None, "real"])
        locator = _make_locator()

        # Must not raise AttributeError (None.strip() would blow up without guard)
        page.select_dropdown(locator, "index", "first_valid", "my-select")

        opts[0].click.assert_not_called()
        opts[1].click.assert_called_once()

    def test_no_valid_option_raises(self):
        """FV-06: when all options are invalid, ElementActionError is raised."""
        page, opts = _make_page_with_options([None, "", "   "])
        locator = _make_locator()

        mock_select_el = page.wait_for_visible.return_value
        sel = Select(mock_select_el)

        with pytest.raises(ElementActionError, match="non-empty value attribute"):
            page._select_first_valid_option(sel, "my-select")

    def test_dispatch_passes_sentinel_to_select_dropdown(self):
        """FV-08: ElementActions.execute() passes 'first_valid' string unchanged to select_dropdown."""
        from src.actions.element_actions import ElementActions
        from src.core.enums import ActionType, ElementType
        from src.models.workflow_models import ElementDefinition

        mock_page = MagicMock()
        mock_wm = MagicMock()
        executor = ElementActions(mock_page, mock_wm)

        el = ElementDefinition(
            name="my-select",
            type=ElementType.SELECT,
            action=ActionType.SELECT_BY_INDEX,
            locator=_make_locator(),
            value="first_valid",
        )
        executor.execute(el, value="first_valid")

        mock_page.select_dropdown.assert_called_once_with(
            el.locator, "index", "first_valid", el.name
        )

    def test_first_valid_in_dom_order(self):
        """FV-09: first qualifying option ('a') is selected, NOT the last ('b')."""
        page, opts = _make_page_with_options(["a", "b"])
        locator = _make_locator()

        page.select_dropdown(locator, "index", "first_valid", "my-select")

        # First option must be clicked; second must NOT
        opts[0].click.assert_called_once()
        opts[1].click.assert_not_called()
