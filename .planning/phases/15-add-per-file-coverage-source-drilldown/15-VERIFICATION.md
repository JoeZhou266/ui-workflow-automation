---
phase: 15-add-per-file-coverage-source-drilldown
verified: 2026-05-31T01:00:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open reports/coverage/custom_index.html in a browser after a full pytest run (without --no-cov)"
    expected: "Page renders with style_cb_*.css applied, package sections show as collapsible <details open> blocks, all 6 columns (File, Stmts, Miss, Branch, BrPart, Cover%) visible, file names are clickable links to per-file pages"
    why_human: "CSS rendering and visual layout require browser inspection; cannot verify via grep"
  - test: "Run pytest twice (first with coverage enabled, then open reports/*.html HTML test report)"
    expected: "'Coverage Report' link appears in each test row's extras section; clicking it opens reports/coverage/index.html in a new tab"
    why_human: "Requires a prior run to have generated reports/coverage/index.html; conditional link rendering requires browser verification"
  - test: "Open a per-file page (reports/coverage/z_src_ui_pages_*.html or similar) in a browser"
    expected: "Yellow highlight on partially-covered branches is visible; page is styled consistently with custom_index.html"
    why_human: "Branch highlighting is rendered by coverage.py's own JS/CSS, not custom code; visual consistency requires browser inspection"
---

# Phase 15: Add Per-File Coverage Source Drilldown — Verification Report

**Phase Goal:** Add per-file coverage source drilldown — JaCoCo-style line-level view per source file linked from HTML coverage report
**Verified:** 2026-05-31T01:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `.coveragerc` has `branch = true` under the `[run]` section | VERIFIED | File line 5: `branch = true`; confirmed before `[html]` section; `TestCoverageRc` (2 tests) all pass |
| 2 | `COVERAGE_DIR = 'reports/coverage'` constant exists in `src/core/constants.py` | VERIFIED | Line 27: `COVERAGE_DIR: str = "reports/coverage"` with `# Coverage` comment; `python3 -c` assertion passes |
| 3 | `build_custom_index()` is importable from `src.utils.coverage_index` | VERIFIED | All 5 exports (`build_custom_index`, `_render_html`, `_render_package`, `_render_row`, `_package_from_path`) import successfully |
| 4 | `build_custom_index()` returns HTML grouped by package with all 6 columns | VERIFIED | `TestBuildCustomIndex` (5 tests) + `TestHtmlStructure` (8 tests) all pass: `<details open>`, `<th>File</th>`, `<th>Stmts</th>`, `<th>Miss</th>`, `<th>Branch</th>`, `<th>BrPart</th>`, `<th>Cover%</th>` confirmed in rendered HTML |
| 5 | Package grouping places `src/ui/pages/x.py` into the `ui` group | VERIFIED | `TestPackageGrouping` (6 tests) all pass; `_package_from_path("src/ui/pages/dynamic_page.py") == "ui"` confirmed; also handles `src/ui/sections/`, backslash separators, top-level fallback |
| 6 | CSS glob produces `style_cb_*.css` href or empty string (no crash) | VERIFIED | `TestCssDiscovery` (2 tests) all pass; empty tmpdir returns valid HTML without reference to `style_cb_`; tmpdir with `style_cb_abc123.css` returns HTML containing that href |
| 7 | Missing `.coverage` file is handled gracefully (guarded by caller) | VERIFIED | `TestMissingCoverageFile` (2 tests) pass; coverage.py 7.10.7 returns empty data (not NoDataError); `pytest_sessionfinish` at line 107 guards with `Path(".coverage").exists()` before calling `build_custom_index` |
| 8 | All COV-01 through COV-06, COV-10, COV-11 unit tests exist and pass | VERIFIED | `pytest tests/unit/test_coverage_index.py -v --no-cov`: 25 passed |
| 9 | `pytest_sessionfinish` hook exists in `tests/conftest.py` with guards and fail-open | VERIFIED | Lines 92-116 in conftest.py; `getattr(config.option, 'no_cov', False)` guard at line 103; `Path(".coverage").exists()` guard at line 107; `try/except Exception` + `warnings.warn` at lines 110-116 |
| 10 | `pytest_runtest_makereport` teardown appends coverage link when index exists | VERIFIED | Lines 70-84 in conftest.py: `coverage_index = Path(HTML_REPORT_DIR) / "coverage" / "index.html"`; guard condition widened to include `coverage_index.exists()`; link with `target='_blank'` and label "Coverage Report" |
| 11 | All COV-07, COV-08, COV-09 unit tests exist and pass | VERIFIED | `pytest tests/unit/test_coverage_conftest.py -v --no-cov`: 14 passed; `TestSessionFinishHook`, `TestNoCovDetection`, `TestCoverageLinkExtras` all present |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.coveragerc` | Branch coverage config with `branch = true` | VERIFIED | Line 5 present under `[run]`; `[html]` section intact |
| `src/core/constants.py` | `COVERAGE_DIR` constant | VERIFIED | Line 27: `COVERAGE_DIR: str = "reports/coverage"` with comment |
| `src/utils/coverage_index.py` | `build_custom_index()` pure function with helpers | VERIFIED | 150 lines; 5 exported functions; `from __future__ import annotations` first line; `html.escape()` on all user-data strings (lines 100, 128, 142) |
| `tests/unit/test_coverage_index.py` | Unit tests for COV-01 through COV-06, COV-10, COV-11 | VERIFIED | 289 lines; 6 test classes; 25 tests; no module-level `src.*` imports |
| `tests/conftest.py` | `pytest_sessionfinish` hook + extended `pytest_runtest_makereport` | VERIFIED | 256 lines; hook at line 92; coverage link at lines 70-84; both wired to `build_custom_index` and `COVERAGE_DIR` |
| `tests/unit/test_coverage_conftest.py` | Unit tests for COV-07, COV-08, COV-09 | VERIFIED | 122 lines; 3 test classes; 14 tests; uses `inspect.getsource()` pattern |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/utils/coverage_index.py` | `coverage.Coverage` | `import coverage; coverage.Coverage` | WIRED | Line 11: `import coverage`; line 41: `factory = _cov_factory if _cov_factory is not None else coverage.Coverage` |
| `src/utils/coverage_index.py` | `coverage.files.flat_rootname` | `from coverage.files import flat_rootname` | WIRED | Line 12: `from coverage.files import flat_rootname`; line 61: `url = flat_rootname(rel) + ".html"` |
| `tests/unit/test_coverage_index.py` | `src/utils/coverage_index.py` | `from src.utils.coverage_index import build_custom_index` | WIRED | Imports inside test methods (correct pattern); 25 tests exercise all functions |
| `tests/conftest.py pytest_sessionfinish` | `src/utils/coverage_index.build_custom_index` | `from src.utils.coverage_index import build_custom_index` | WIRED | Line 14; called at line 111: `html = build_custom_index(coverage_dir=COVERAGE_DIR)` |
| `tests/conftest.py pytest_sessionfinish` | `src/core/constants.COVERAGE_DIR` | `from src.core.constants import COVERAGE_DIR` | WIRED | Line 13; used at lines 111-112 |
| `tests/conftest.py pytest_runtest_makereport` | `reports/coverage/index.html` | `Path(HTML_REPORT_DIR) / "coverage" / "index.html"` | WIRED | Lines 70-83; `.exists()` guard present; link rendered conditionally |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `coverage_index.py build_custom_index()` | `packages` dict | `cov._analyze(abs_path).numbers` via `coverage.py` API | Yes — reads from `.coverage` binary; mocked in tests via `_cov_factory` injectable | FLOWING |
| `conftest.py pytest_sessionfinish` | `html` string | `build_custom_index(coverage_dir=COVERAGE_DIR)` | Yes — delegates to real coverage data; writes to `custom_index.html` | FLOWING |
| `conftest.py pytest_runtest_makereport` | coverage link HTML | Hardcoded string `'<p><a href="coverage/index.html" target="_blank">Coverage Report</a></p>'` | N/A — static link, no dynamic data | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All phase 15 unit tests pass | `pytest tests/unit/test_coverage_index.py tests/unit/test_coverage_conftest.py -v --no-cov` | 39 passed in 0.04s | PASS |
| Full unit suite passes (no regressions) | `pytest tests/unit/ -v --no-cov` | 363 passed in 0.29s | PASS |
| All 5 exports importable | `python3 -c "from src.utils.coverage_index import build_custom_index, _package_from_path, _render_html, _render_package, _render_row"` | Exit 0 | PASS |
| COVERAGE_DIR constant value | `python3 -c "from src.core.constants import COVERAGE_DIR; assert COVERAGE_DIR == 'reports/coverage'"` | Exit 0 | PASS |
| pytest_sessionfinish hook callable with all guards | `python3 -c "import inspect, tests.conftest as c; src = inspect.getsource(c.pytest_sessionfinish); assert all(s in src for s in ['no_cov', 'build_custom_index', '.coverage', 'warnings.warn'])"` | Exit 0 | PASS |
| Coverage link in makereport | `python3 -c "import inspect, tests.conftest as c; src = inspect.getsource(c.pytest_runtest_makereport); assert all(s in src for s in ['coverage/index.html', 'Coverage Report', '.exists()'])"` | Exit 0 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| COV-01 | 15-01 | `branch = true` in `.coveragerc` | SATISFIED | `.coveragerc` line 5; `TestCoverageRc` 2 tests pass |
| COV-02 | 15-01 | `build_custom_index()` returns HTML with all packages | SATISFIED | `TestBuildCustomIndex` 5 tests pass; HTML contains `actions/`, `core/`, file links, `Overall:` |
| COV-03 | 15-01 | Package grouping: `src/ui/pages/x.py` → `ui` | SATISFIED | `TestPackageGrouping` 6 tests pass; includes Windows path separator handling |
| COV-04 | 15-01 | CSS glob returns correct `style_cb_*.css` href | SATISFIED | `TestCssDiscovery::test_css_href_used_when_css_present` passes |
| COV-05 | 15-01 | `<details open>` present for each package group | SATISFIED | `TestHtmlStructure::test_details_open_present` passes; `_render_package()` emits `<details open>` |
| COV-06 | 15-01 | File rows include all 6 columns | SATISFIED | `TestHtmlStructure` 6 column-header tests all pass |
| COV-07 | 15-02 | `pytest_sessionfinish` hook exists in conftest | SATISFIED | `TestSessionFinishHook` 7 tests pass; hook at line 92 |
| COV-08 | 15-02 | `--no-cov` detection via `config.option.no_cov` | SATISFIED | `TestNoCovDetection` 3 tests pass; `getattr(config.option, 'no_cov', False)` at line 103 |
| COV-09 | 15-02 | Coverage link in `pytest_runtest_makereport` teardown extras | SATISFIED | `TestCoverageLinkExtras` 4 tests pass; link at lines 80-83 |
| COV-10 | 15-01 | Missing `.coverage` file: handled gracefully | SATISFIED | `TestMissingCoverageFile` 2 tests pass (adjusted from plan: coverage.py 7.10.7 returns empty HTML rather than raising NoDataError; caller guard in `pytest_sessionfinish` covers both paths) |
| COV-11 | 15-01 | `build_custom_index()` with empty CSS glob: no crash | SATISFIED | `TestCssDiscovery::test_css_href_empty_when_no_css_files` passes; returns valid HTML with no `style_cb_` reference |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/utils/coverage_index.py` | 38-39 | Docstring `Raises: coverage.exceptions.NoDataError` is stale — coverage.py 7.10.7 does not raise this; function returns empty HTML instead | Info | No functional impact; documentation mismatch only; caller guard in conftest handles both paths correctly |

### Human Verification Required

#### 1. Custom Index HTML visual rendering

**Test:** Run `pytest` without `--no-cov` to generate `.coverage` and `reports/coverage/`, then open `reports/coverage/custom_index.html` in a browser.
**Expected:** Page renders styled with `style_cb_*.css` (matching coverage.py's built-in pages), package sections display as collapsible `<details open>` blocks, all 6 columns (File, Stmts, Miss, Branch, BrPart, Cover%) visible in each table, file names are hyperlinks to per-file `z_*.html` pages.
**Why human:** CSS rendering and visual layout cannot be verified via grep or CLI commands.

#### 2. Coverage link in pytest HTML report extras

**Test:** Run `pytest` once with coverage enabled (no `--no-cov`), then open the generated `reports/*.html` test report in a browser and inspect any test row's extras section.
**Expected:** "Coverage Report" link appears in the extras section. Clicking it opens `reports/coverage/index.html` in a new browser tab.
**Why human:** This requires a prior run to have generated `reports/coverage/index.html` so the conditional check fires; the conditional rendering and link navigation require browser verification.

#### 3. Per-file branch highlighting

**Test:** Open a per-file coverage page (e.g., `reports/coverage/z_src_utils_coverage_index_py.html`) in a browser after a test run.
**Expected:** Partially-covered branches are highlighted in yellow (coverage.py's standard rendering). The page is visually consistent with the rest of the coverage report.
**Why human:** Branch highlighting is rendered by coverage.py's built-in JS/CSS, not custom code; visual consistency requires browser inspection.

### Gaps Summary

No gaps. All 11 must-haves are verified at all levels (exists, substantive, wired, data-flowing). The phase goal is achieved: `build_custom_index()` generates a JaCoCo-style grouped HTML index per source file, wired into the pytest session via `pytest_sessionfinish`, with a link from the HTML test report via `pytest_runtest_makereport`. Three human verification items exist for visual/browser rendering, which cannot be verified programmatically.

**Note on COV-10 deviation:** The plan originally specified `build_custom_index()` should raise `NoDataError` on missing `.coverage` file. Investigation during implementation revealed that coverage.py 7.10.7 does NOT raise — it returns empty data silently. The test was auto-fixed to verify the actual fail-open behavior (returns valid empty HTML). The docstring in `coverage_index.py` still documents `NoDataError` which is now stale (info-level inconsistency only). The caller guard in `pytest_sessionfinish` (`Path(".coverage").exists()` check) correctly handles this case regardless.

---

_Verified: 2026-05-31T01:00:00Z_
_Verifier: Claude (gsd-verifier)_
