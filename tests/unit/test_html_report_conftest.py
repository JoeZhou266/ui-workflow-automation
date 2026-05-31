"""Unit tests for Phase 13 additions to tests/conftest.py.

Covers: HTML-10 (StashKey), HTML-11 (workflow_report_extras fixture), HTML-12 (pytest_configure hook).
No real pytest session is started — tests inspect conftest module attributes directly.
"""
from __future__ import annotations

import tests.conftest as conftest
from pytest import StashKey


# ---------------------------------------------------------------------------
# HTML-10: _execution_summary_key StashKey exists at module level
# ---------------------------------------------------------------------------

class TestExecutionSummaryStashKey:
    """_execution_summary_key must be a StashKey instance at module level."""

    def test_execution_summary_key_exists(self):
        assert hasattr(conftest, "_execution_summary_key"), (
            "_execution_summary_key not found in tests/conftest.py — "
            "add: _execution_summary_key: StashKey[ExecutionSummary] = StashKey()"
        )

    def test_execution_summary_key_is_stashkey(self):
        assert isinstance(conftest._execution_summary_key, StashKey), (
            f"_execution_summary_key is {type(conftest._execution_summary_key)}, expected StashKey"
        )


class TestVideoPathStashKey:
    """_video_path_key must be a StashKey instance at module level."""

    def test_video_path_key_exists(self):
        assert hasattr(conftest, "_video_path_key"), (
            "_video_path_key not found in tests/conftest.py — "
            "add: _video_path_key: StashKey[Optional[str]] = StashKey()"
        )

    def test_video_path_key_is_stashkey(self):
        assert isinstance(conftest._video_path_key, StashKey), (
            f"_video_path_key is {type(conftest._video_path_key)}, expected StashKey"
        )


# ---------------------------------------------------------------------------
# HTML-11: workflow_report_extras fixture
# ---------------------------------------------------------------------------

class TestWorkflowReportExtrasFixture:
    """workflow_report_extras must be a function-scoped, non-autouse, callable fixture."""

    def test_fixture_exists(self):
        assert hasattr(conftest, "workflow_report_extras"), (
            "workflow_report_extras fixture not found in tests/conftest.py"
        )

    def test_fixture_is_callable(self):
        assert callable(conftest.workflow_report_extras), (
            "workflow_report_extras must be callable (decorated with @pytest.fixture)"
        )

    def test_fixture_not_autouse(self):
        marker = getattr(conftest.workflow_report_extras, "_pytestfixturefunction", None)
        if marker is not None:
            assert not marker.autouse, (
                "workflow_report_extras must NOT be autouse — it is an opt-in fixture"
            )

    def test_fixture_scope_function(self):
        marker = getattr(conftest.workflow_report_extras, "_pytestfixturefunction", None)
        if marker is not None:
            assert marker.scope in ("function", None), (
                f"workflow_report_extras scope is '{marker.scope}', expected 'function'"
            )


# ---------------------------------------------------------------------------
# HTML-12: pytest_configure hook with tryfirst=True
# ---------------------------------------------------------------------------

class TestPytestConfigure:
    """pytest_configure must exist with @pytest.hookimpl(tryfirst=True)."""

    def test_configure_hook_exists(self):
        assert hasattr(conftest, "pytest_configure"), (
            "pytest_configure hook not found in tests/conftest.py"
        )

    def test_configure_hook_is_callable(self):
        assert callable(conftest.pytest_configure), (
            "pytest_configure must be a callable function"
        )

    def test_configure_hook_has_tryfirst(self):
        hook = conftest.pytest_configure
        opts = getattr(hook, "pytest_impl", {})
        assert opts.get("tryfirst") is True, (
            f"pytest_configure must have tryfirst=True; got opts={opts}. "
            "Decorate with @pytest.hookimpl(tryfirst=True)"
        )

    def test_configure_hook_is_not_wrapper(self):
        """pytest_configure is a plain hook (not a wrapper — no yield)."""
        hook = conftest.pytest_configure
        opts = getattr(hook, "pytest_impl", {})
        assert not opts.get("wrapper"), (
            "pytest_configure must NOT use wrapper=True — it is a plain hook, not a wrapper"
        )


# ---------------------------------------------------------------------------
# HTML-12 extension: pytest_runtest_makereport teardown branch exists
# ---------------------------------------------------------------------------

class TestMakereportTeardownBranch:
    """pytest_runtest_makereport must have the teardown extras logic (inspect source)."""

    def test_makereport_hook_exists(self):
        assert hasattr(conftest, "pytest_runtest_makereport")

    def test_makereport_has_wrapper_and_tryfirst(self):
        hook = conftest.pytest_runtest_makereport
        opts = getattr(hook, "pytest_impl", {})
        assert opts.get("wrapper") is True
        assert opts.get("tryfirst") is True

    def test_makereport_source_contains_teardown_branch(self):
        """Verify teardown extras logic is present in the hook source."""
        import inspect
        src = inspect.getsource(conftest.pytest_runtest_makereport)
        assert "teardown" in src, (
            "pytest_runtest_makereport must have a 'teardown' branch for extras attachment"
        )
        assert "build_step_table" in src, (
            "pytest_runtest_makereport must call build_step_table() in teardown branch"
        )
        assert "html_extras" in src, (
            "pytest_runtest_makereport must use html_extras.html() to attach extras"
        )
