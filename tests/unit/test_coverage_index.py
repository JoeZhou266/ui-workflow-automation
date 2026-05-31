"""Unit tests for coverage_index utility.

Covers: COV-01 through COV-06, COV-10, COV-11
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Mock factory for Coverage objects (avoids needing a real .coverage file)
# ---------------------------------------------------------------------------

def _make_mock_numbers(stmts=10, miss=2, branch=4, brpart=1, pct=80.0):
    """Build a mock Numbers-like object."""
    nums = MagicMock()
    nums.n_statements = stmts
    nums.n_missing = miss
    nums.n_branches = branch
    nums.n_partial_branches = brpart
    nums.pc_covered = pct
    return nums


def _make_mock_analysis(stmts=10, miss=2, branch=4, brpart=1, pct=80.0):
    analysis = MagicMock()
    analysis.numbers = _make_mock_numbers(stmts, miss, branch, brpart, pct)
    return analysis


def _make_mock_cov_factory(files_by_relpath: dict):
    """Return a _cov_factory callable for build_custom_index().

    files_by_relpath: {"src/actions/action_factory.py": {"stmts": 10, ...}}
    """
    def factory(data_file=".coverage"):
        cov = MagicMock()
        # Resolve to abs paths as measured_files() returns abs paths
        abs_files = {
            os.path.abspath(rel): stats
            for rel, stats in files_by_relpath.items()
        }
        cov.get_data.return_value.measured_files.return_value = sorted(abs_files.keys())
        def _analyze(abs_path):
            stats = abs_files[abs_path]
            return _make_mock_analysis(**stats)
        cov._analyze.side_effect = _analyze
        return cov
    return factory


# ---------------------------------------------------------------------------
# COV-01: branch = true exists in .coveragerc
# ---------------------------------------------------------------------------

class TestCoverageRc:
    """COV-01: .coveragerc must have branch = true under [run]."""

    def test_branch_true_in_coveragerc(self):
        coveragerc = Path(".coveragerc")
        assert coveragerc.exists(), ".coveragerc not found in project root"
        content = coveragerc.read_text()
        assert "branch = true" in content, (
            ".coveragerc must contain 'branch = true' under [run]; "
            f"got:\n{content}"
        )

    def test_branch_under_run_section(self):
        coveragerc = Path(".coveragerc")
        content = coveragerc.read_text()
        run_section = content.split("[html]")[0]  # everything before [html]
        assert "branch = true" in run_section, (
            "'branch = true' must be under [run], not [html]; "
            f"[run] section:\n{run_section}"
        )


# ---------------------------------------------------------------------------
# COV-02: build_custom_index() returns HTML with all packages
# ---------------------------------------------------------------------------

class TestBuildCustomIndex:
    """COV-02: build_custom_index() returns HTML string with package groups."""

    def _two_package_factory(self):
        return _make_mock_cov_factory({
            "src/actions/action_factory.py": {"stmts": 41, "miss": 0, "branch": 12, "brpart": 0, "pct": 100.0},
            "src/core/constants.py": {"stmts": 30, "miss": 5, "branch": 0, "brpart": 0, "pct": 83.0},
        })

    def test_returns_string(self):
        from src.utils.coverage_index import build_custom_index
        factory = self._two_package_factory()
        html = build_custom_index(_cov_factory=factory)
        assert isinstance(html, str), f"Expected str; got {type(html)}"

    def test_contains_doctype(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._two_package_factory())
        assert "<!DOCTYPE html>" in html, "HTML must start with <!DOCTYPE html>"

    def test_contains_both_packages(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._two_package_factory())
        assert "actions/" in html, "HTML must contain 'actions/' package section"
        assert "core/" in html, "HTML must contain 'core/' package section"

    def test_contains_file_link(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._two_package_factory())
        assert "action_factory.py" in html, (
            "HTML must contain file link to action_factory.py"
        )

    def test_contains_overall_pct(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._two_package_factory())
        assert "Overall:" in html, "HTML must contain 'Overall:' summary line"


# ---------------------------------------------------------------------------
# COV-03: Package grouping — src/ui/pages/x.py -> ui
# ---------------------------------------------------------------------------

class TestPackageGrouping:
    """COV-03: _package_from_path extracts the correct src/ subpackage."""

    def test_actions_package(self):
        from src.utils.coverage_index import _package_from_path
        assert _package_from_path("src/actions/action_factory.py") == "actions"

    def test_ui_nested_pages(self):
        from src.utils.coverage_index import _package_from_path
        assert _package_from_path("src/ui/pages/dynamic_page.py") == "ui", (
            "Nested path src/ui/pages/ must group under 'ui', not 'pages'"
        )

    def test_ui_nested_sections(self):
        from src.utils.coverage_index import _package_from_path
        assert _package_from_path("src/ui/sections/dynamic_section.py") == "ui"

    def test_core_package(self):
        from src.utils.coverage_index import _package_from_path
        assert _package_from_path("src/core/constants.py") == "core"

    def test_top_level_falls_back_to_root(self):
        from src.utils.coverage_index import _package_from_path
        assert _package_from_path("top_level.py") == "root"

    def test_windows_path_separator(self):
        from src.utils.coverage_index import _package_from_path
        assert _package_from_path("src\\actions\\action_factory.py") == "actions", (
            "Must handle Windows backslash separators"
        )


# ---------------------------------------------------------------------------
# COV-04, COV-11: CSS discovery — style_cb_*.css found / not found
# ---------------------------------------------------------------------------

class TestCssDiscovery:
    """COV-04: CSS href discovered via glob; COV-11: no crash when CSS absent."""

    def test_css_href_empty_when_no_css_files(self):
        from src.utils.coverage_index import build_custom_index
        factory = _make_mock_cov_factory({
            "src/actions/action_factory.py": {"stmts": 10, "miss": 0, "branch": 0, "brpart": 0, "pct": 100.0},
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            html = build_custom_index(coverage_dir=tmpdir, _cov_factory=factory)
        # No CSS file — must not crash, must return valid HTML
        assert "<!DOCTYPE html>" in html, "Must return valid HTML even without CSS"
        assert "style_cb_" not in html, "Should not reference missing CSS file"

    def test_css_href_used_when_css_present(self):
        from src.utils.coverage_index import build_custom_index
        factory = _make_mock_cov_factory({
            "src/actions/action_factory.py": {"stmts": 10, "miss": 0, "branch": 0, "brpart": 0, "pct": 100.0},
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            css_path = os.path.join(tmpdir, "style_cb_abc123.css")
            Path(css_path).write_text("body {}")
            html = build_custom_index(coverage_dir=tmpdir, _cov_factory=factory)
        assert "style_cb_abc123.css" in html, (
            f"CSS href must appear in HTML when present; got html[:300]={html[:300]}"
        )


# ---------------------------------------------------------------------------
# COV-05, COV-06: HTML structure — <details open> and column headers
# ---------------------------------------------------------------------------

class TestHtmlStructure:
    """COV-05: <details open> per package; COV-06: all 6 column headers present."""

    def _factory(self):
        return _make_mock_cov_factory({
            "src/actions/action_factory.py": {"stmts": 41, "miss": 0, "branch": 12, "brpart": 0, "pct": 100.0},
            "src/core/constants.py": {"stmts": 30, "miss": 5, "branch": 0, "brpart": 0, "pct": 83.0},
        })

    def test_details_open_present(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._factory())
        assert "<details open>" in html, (
            "Package sections must use <details open> (D-05), not <details>"
        )

    def test_file_column_header(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._factory())
        assert "<th>File</th>" in html, "Table must have 'File' column header"

    def test_stmts_column_header(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._factory())
        assert "<th>Stmts</th>" in html, "Table must have 'Stmts' column header"

    def test_miss_column_header(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._factory())
        assert "<th>Miss</th>" in html, "Table must have 'Miss' column header"

    def test_branch_column_header(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._factory())
        assert "<th>Branch</th>" in html, "Table must have 'Branch' column header (D-03)"

    def test_brpart_column_header(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._factory())
        assert "<th>BrPart</th>" in html, "Table must have 'BrPart' column header (D-03)"

    def test_cover_pct_column_header(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._factory())
        assert "<th>Cover%</th>" in html, "Table must have 'Cover%' column header"

    def test_package_summary_line_shows_pct(self):
        from src.utils.coverage_index import build_custom_index
        html = build_custom_index(_cov_factory=self._factory())
        # actions/ has 0 miss, 41 stmts -> 100%
        assert "actions/ (100%)" in html, (
            "Package summary must show coverage percentage: 'actions/ (100%)'"
        )


# ---------------------------------------------------------------------------
# COV-10: Missing .coverage file — graceful handling
# ---------------------------------------------------------------------------

class TestMissingCoverageFile:
    """COV-10: build_custom_index() with missing data file is handled gracefully.

    coverage.py 7.10.7 does NOT raise NoDataError when .coverage is absent —
    it loads empty data and returns an empty file list. The caller (pytest_sessionfinish)
    guards with Path(".coverage").exists() before calling build_custom_index.
    build_custom_index itself should return valid empty HTML (not crash) when
    data_file is missing — fail-open behavior.
    """

    def test_returns_valid_html_on_missing_data_file(self):
        from src.utils.coverage_index import build_custom_index
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = os.path.join(tmpdir, "nonexistent.coverage")
            # coverage.Coverage.load() with missing file returns empty data (no exception)
            # build_custom_index should return valid HTML (no files, 0% overall)
            html = build_custom_index(coverage_dir=tmpdir, data_file=missing)
            assert isinstance(html, str), "Must return a string even with missing data file"
            assert "<!DOCTYPE html>" in html, "Must return valid HTML even with missing data file"

    def test_no_crash_on_missing_data_file(self):
        from src.utils.coverage_index import build_custom_index
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = os.path.join(tmpdir, "nonexistent.coverage")
            # Must not raise — caller guards existence check before calling this
            try:
                build_custom_index(coverage_dir=tmpdir, data_file=missing)
            except Exception as exc:
                pytest.fail(
                    f"build_custom_index must not crash on missing data file; "
                    f"got {type(exc).__name__}: {exc}"
                )
