"""Unit tests for Phase 15 additions to tests/conftest.py.

Covers: COV-07 (pytest_sessionfinish hook), COV-08 (--no-cov detection),
        COV-09 (coverage link in pytest_runtest_makereport teardown extras).
No real pytest session is started — tests inspect conftest module attributes directly.
"""
from __future__ import annotations

import inspect

import tests.conftest as conftest


# ---------------------------------------------------------------------------
# COV-07: pytest_sessionfinish hook exists
# ---------------------------------------------------------------------------

class TestSessionFinishHook:
    """pytest_sessionfinish must exist as a callable in tests/conftest.py."""

    def test_hook_exists(self):
        assert hasattr(conftest, "pytest_sessionfinish"), (
            "pytest_sessionfinish hook not found in tests/conftest.py — "
            "add: def pytest_sessionfinish(session, exitstatus): ..."
        )

    def test_hook_is_callable(self):
        assert callable(conftest.pytest_sessionfinish), (
            f"pytest_sessionfinish is {type(conftest.pytest_sessionfinish)}, expected callable"
        )

    def test_hook_has_two_parameters(self):
        sig = inspect.signature(conftest.pytest_sessionfinish)
        params = list(sig.parameters)
        assert params == ["session", "exitstatus"], (
            f"pytest_sessionfinish must accept (session, exitstatus); got: {params}"
        )

    def test_hook_calls_build_custom_index(self):
        src = inspect.getsource(conftest.pytest_sessionfinish)
        assert "build_custom_index" in src, (
            "pytest_sessionfinish must call build_custom_index() (D-13, D-14)"
        )

    def test_hook_writes_custom_index_html(self):
        src = inspect.getsource(conftest.pytest_sessionfinish)
        assert "custom_index.html" in src, (
            "pytest_sessionfinish must write custom_index.html to COVERAGE_DIR"
        )

    def test_hook_has_fail_open_exception_handler(self):
        src = inspect.getsource(conftest.pytest_sessionfinish)
        assert "except Exception" in src or "except Exception as" in src, (
            "pytest_sessionfinish must have a fail-open except Exception handler (RESEARCH.md pitfall)"
        )

    def test_hook_uses_warnings_warn(self):
        src = inspect.getsource(conftest.pytest_sessionfinish)
        assert "warnings.warn" in src, (
            "pytest_sessionfinish must use warnings.warn (not logger) for fail-open reporting"
        )


# ---------------------------------------------------------------------------
# COV-08: --no-cov detection in pytest_sessionfinish
# ---------------------------------------------------------------------------

class TestNoCovDetection:
    """pytest_sessionfinish must check config.option.no_cov (D-11)."""

    def test_sessionfinish_checks_no_cov(self):
        src = inspect.getsource(conftest.pytest_sessionfinish)
        assert "no_cov" in src, (
            "pytest_sessionfinish must check config.option.no_cov to respect --no-cov flag (D-11)"
        )

    def test_sessionfinish_checks_coverage_data_file(self):
        src = inspect.getsource(conftest.pytest_sessionfinish)
        assert ".coverage" in src, (
            "pytest_sessionfinish must check for .coverage file existence before loading (D-14, pitfall 2)"
        )

    def test_sessionfinish_uses_getattr_for_no_cov(self):
        src = inspect.getsource(conftest.pytest_sessionfinish)
        # getattr with default avoids AttributeError when no_cov is not set
        assert "getattr" in src, (
            "pytest_sessionfinish should use getattr(config.option, 'no_cov', False) "
            "to safely access the attribute without AttributeError"
        )


# ---------------------------------------------------------------------------
# COV-09: coverage link in pytest_runtest_makereport teardown extras
# ---------------------------------------------------------------------------

class TestCoverageLinkExtras:
    """pytest_runtest_makereport teardown must append a coverage/index.html link (D-08, D-09, D-10)."""

    def test_makereport_source_contains_coverage_link(self):
        src = inspect.getsource(conftest.pytest_runtest_makereport)
        assert "coverage/index.html" in src, (
            "pytest_runtest_makereport must append 'coverage/index.html' link to extras (D-08)"
        )

    def test_makereport_source_contains_coverage_report_label(self):
        src = inspect.getsource(conftest.pytest_runtest_makereport)
        assert "Coverage Report" in src, (
            "pytest_runtest_makereport coverage link must have label 'Coverage Report' (D-09)"
        )

    def test_makereport_source_contains_conditional_exists_check(self):
        src = inspect.getsource(conftest.pytest_runtest_makereport)
        assert ".exists()" in src, (
            "Coverage link must only be rendered when reports/coverage/index.html exists (D-10)"
        )

    def test_makereport_source_has_teardown_branch(self):
        src = inspect.getsource(conftest.pytest_runtest_makereport)
        assert "teardown" in src, (
            "pytest_runtest_makereport must have a 'teardown' branch for extras attachment"
        )
