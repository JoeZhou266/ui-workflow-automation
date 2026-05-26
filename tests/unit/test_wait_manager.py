"""Unit tests for WaitManager._dispatch() — no real browser required."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.core.enums import WaitConditionType
from src.models.workflow_models import WaitConditionDefinition
from src.waits.wait_manager import WaitManager


@pytest.fixture
def mock_driver():
    return MagicMock()


@pytest.fixture
def wm(mock_driver):
    return WaitManager(mock_driver, default_timeout=10, default_poll_ms=500)


class TestWaitSecondsDispatch:
    def test_wait_seconds_calls_time_sleep_with_timeout(self, wm):
        cdef = WaitConditionDefinition(
            condition=WaitConditionType.WAIT_SECONDS,
            timeout=2,
        )
        with patch("src.waits.wait_manager.time.sleep") as mock_sleep:
            wm.wait_for_condition(cdef, element_name="pause_step")
        mock_sleep.assert_called_once_with(2)

    def test_wait_seconds_does_not_call_wait_for(self, wm):
        cdef = WaitConditionDefinition(
            condition=WaitConditionType.WAIT_SECONDS,
            timeout=3,
        )
        with patch("src.waits.wait_manager.time.sleep"), \
             patch.object(wm, "wait_for") as mock_wait_for:
            wm.wait_for_condition(cdef)
        mock_wait_for.assert_not_called()

    def test_wait_seconds_logs_at_warning_level(self, wm, caplog):
        cdef = WaitConditionDefinition(
            condition=WaitConditionType.WAIT_SECONDS,
            timeout=1,
        )
        with patch("src.waits.wait_manager.time.sleep"):
            with caplog.at_level(logging.WARNING, logger="wait_manager"):
                wm.wait_for_condition(cdef)
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any(
            "wait_seconds" in r.message.lower() or "sleeping" in r.message.lower()
            for r in warnings
        ), f"Expected WARNING log mentioning wait_seconds/sleeping; got: {[r.message for r in warnings]}"

    def test_wait_seconds_uses_sleep_seconds_helper(self, wm):
        cdef = WaitConditionDefinition(
            condition=WaitConditionType.WAIT_SECONDS,
            timeout=5,
        )
        with patch.object(WaitManager, "_sleep_seconds") as mock_helper:
            wm.wait_for_condition(cdef)
        mock_helper.assert_called_once_with(5)

    def test_wait_seconds_as_pre_wait_simulates_pre_wait_call(self, wm):
        cdef = WaitConditionDefinition(
            condition=WaitConditionType.WAIT_SECONDS,
            timeout=1,
        )
        with patch("src.waits.wait_manager.time.sleep") as mock_sleep:
            wm.wait_for_condition(cdef, element_name="my_pre_step")
        mock_sleep.assert_called_once_with(1)

    def test_wait_seconds_as_post_wait_simulates_post_wait_call(self, wm):
        cdef = WaitConditionDefinition(
            condition=WaitConditionType.WAIT_SECONDS,
            timeout=4,
        )
        with patch("src.waits.wait_manager.time.sleep") as mock_sleep:
            wm.wait_for_condition(cdef, element_name="my_post_step")
        mock_sleep.assert_called_once_with(4)

    def test_wait_seconds_with_no_locator_does_not_raise(self, wm):
        cdef = WaitConditionDefinition(
            condition=WaitConditionType.WAIT_SECONDS,
            timeout=2,
            locator=None,
        )
        with patch("src.waits.wait_manager.time.sleep"):
            wm.wait_for_condition(cdef)

    def test_wait_seconds_bypasses_pre_checks_when_require_document_ready_set(self, wm):
        """WAIT_SECONDS must short-circuit before the readiness pre-checks.

        Even if require_document_ready=True is set, the sleep should execute
        immediately and wait_for must never be called — the early-return guard
        prevents WaitTimeoutError from firing against an unloaded page.
        """
        cdef = WaitConditionDefinition(
            condition=WaitConditionType.WAIT_SECONDS,
            timeout=3,
            require_document_ready=True,
        )
        with patch("src.waits.wait_manager.time.sleep") as mock_sleep, \
             patch.object(wm, "wait_for") as mock_wait_for:
            wm.wait_for_condition(cdef, element_name="pause_before_nav")
        mock_sleep.assert_called_once_with(3)
        mock_wait_for.assert_not_called()
