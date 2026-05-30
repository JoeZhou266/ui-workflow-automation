"""
Tests for the pytest_runtest_makereport hook and StashKey constant added to conftest.py.
TDD RED: these tests fail until conftest.py is updated.
"""
from __future__ import annotations

import tests.conftest as conftest
from pytest import StashKey


class TestStashKeyConstant:
    """_phase_report_key must be a StashKey instance at module level."""

    def test_phase_report_key_exists(self):
        assert hasattr(conftest, "_phase_report_key"), (
            "_phase_report_key not found in tests/conftest.py"
        )

    def test_phase_report_key_is_stashkey(self):
        assert isinstance(conftest._phase_report_key, StashKey), (
            f"_phase_report_key is {type(conftest._phase_report_key)}, expected StashKey"
        )


class TestHookPresence:
    """pytest_runtest_makereport hook must be a callable at module level."""

    def test_hook_exists(self):
        assert hasattr(conftest, "pytest_runtest_makereport"), (
            "pytest_runtest_makereport not found in tests/conftest.py"
        )

    def test_hook_is_callable(self):
        assert callable(conftest.pytest_runtest_makereport), (
            "pytest_runtest_makereport is not callable"
        )

    def test_hook_has_hookimpl_marker(self):
        """The hook must be decorated with @pytest.hookimpl(wrapper=True, tryfirst=True)."""
        hook = conftest.pytest_runtest_makereport
        # pytest.hookimpl decorator attaches a pytestmark attribute to the function
        assert hasattr(hook, "pytestmark") or hasattr(hook, "hookwrapper") or hasattr(hook, "_pytestwrap"), (
            "pytest_runtest_makereport does not appear to have a @pytest.hookimpl marker"
        )

    def test_hook_not_hookwrapper(self):
        """Must use wrapper=True (new style), not hookwrapper=True (deprecated)."""
        import inspect
        source = inspect.getsource(conftest.pytest_runtest_makereport)
        assert "hookwrapper=True" not in source, (
            "hook uses deprecated hookwrapper=True; must use wrapper=True"
        )
        assert "wrapper=True" in source or "tryfirst=True" in source, (
            "hook source does not contain wrapper=True or tryfirst=True"
        )
