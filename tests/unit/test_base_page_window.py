"""Unit tests for BasePage window management methods using mocked Selenium."""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch
import pytest


def _make_page():
    from src.ui.base_page import BasePage

    page = BasePage.__new__(BasePage)
    page._driver = MagicMock()
    page._wm = MagicMock()
    page._screenshots = MagicMock()
    return page


class TestOpenNewWindow:
    def test_calls_switch_to_new_window_with_window_hint(self):
        page = _make_page()
        page.open_new_window("window")
        page._driver.switch_to.new_window.assert_called_once_with("window")

    def test_calls_switch_to_new_window_with_tab_hint(self):
        page = _make_page()
        page.open_new_window("tab")
        page._driver.switch_to.new_window.assert_called_once_with("tab")

    def test_default_type_hint_is_window(self):
        page = _make_page()
        page.open_new_window()
        page._driver.switch_to.new_window.assert_called_once_with("window")


class TestSwitchToLatestWindow:
    def test_waits_then_switches_to_new_handle(self):
        page = _make_page()
        old_handle = "handle-1"
        new_handle = "handle-2"

        page._driver.window_handles = [old_handle]

        def fake_wait_for(condition, description, timeout=None):
            page._driver.window_handles = [old_handle, new_handle]

        page._wm.wait_for.side_effect = fake_wait_for

        page.switch_to_latest_window()

        page._driver.switch_to.window.assert_called_once_with(new_handle)

    def test_uses_set_difference_not_index(self):
        """New handle must be identified by set subtraction, not [-1] index."""
        page = _make_page()
        handle_a = "handle-a"
        handle_b = "handle-b"
        page._driver.window_handles = [handle_a]

        def fake_wait_for(condition, description, timeout=None):
            page._driver.window_handles = [handle_a, handle_b]

        page._wm.wait_for.side_effect = fake_wait_for
        page.switch_to_latest_window()
        page._driver.switch_to.window.assert_called_once_with(handle_b)

    def test_passes_timeout_to_wait_manager(self):
        """Custom timeout must be forwarded to self._wm.wait_for."""
        page = _make_page()
        old_handle = "original"
        page._driver.window_handles = [old_handle]

        def fake_wait_for(condition, description, timeout=None):
            page._driver.window_handles = [old_handle, "new-one"]

        page._wm.wait_for.side_effect = fake_wait_for
        page.switch_to_latest_window(timeout=5)

        page._wm.wait_for.assert_called_once()
        _, kwargs = page._wm.wait_for.call_args
        assert kwargs.get("timeout") == 5
