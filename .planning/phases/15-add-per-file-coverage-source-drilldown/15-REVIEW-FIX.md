---
phase: 15-add-per-file-coverage-source-drilldown
fixed_at: 2026-05-31T08:56:00Z
review_path: .planning/phases/15-add-per-file-coverage-source-drilldown/15-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 15: Code Review Fix Report

**Fixed at:** 2026-05-31T08:56:00Z
**Source review:** .planning/phases/15-add-per-file-coverage-source-drilldown/15-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: Negative overall coverage percentage when miss > stmts

**Files modified:** `src/utils/coverage_index.py`
**Commit:** 5b20aff
**Applied fix:** Added `raw_pct` intermediate variable and `overall_pct = max(0, min(100, raw_pct))` clamping at line 76-77. Applied the same clamp pattern to `pkg_pct` in `_render_package()` at line 126-127 using `raw_pkg_pct` intermediate.

---

### WR-02: Non-deterministic CSS file selection when multiple style_cb_*.css files exist

**Files modified:** `src/utils/coverage_index.py`
**Commit:** 5b20aff
**Applied fix:** Wrapped `glob.glob(...)` with `sorted()` and changed `css_files[0]` to `css_files[-1]` to select the last (newest hash) CSS file deterministically across all OS filesystems.

---

### WR-03: `.coverage` path guard in conftest does not match configurable data_file

**Files modified:** `tests/conftest.py`
**Commit:** 10cd0f5
**Applied fix:**
- Moved `import warnings` from inside the `except` block to module-level imports (PEP 8).
- Added `import coverage as _cov_mod` at module level.
- Replaced hard-coded `Path(".coverage").exists()` guard with `_cov_mod.Coverage().config.data_file` to resolve the actual data file path, respecting both `COVERAGE_FILE` environment variable and `.coveragerc` `[run] data_file` settings.
- Passed the resolved `_data_file` to `build_custom_index()` for consistency.

---

### WR-04: Missing `.coverage` test uses real coverage.py with undocumented version assumption

**Files modified:** `tests/unit/test_coverage_index.py`
**Commit:** 4ddc399
**Applied fix:** Added `_empty_factory` instance method to `TestMissingCoverageFile` that returns a `MagicMock` coverage object with `measured_files()` returning an empty list. Both `test_returns_valid_html_on_missing_data_file` and `test_no_crash_on_missing_data_file` now pass `_cov_factory=self._empty_factory` instead of instantiating a real `coverage.Coverage` object against a nonexistent file. Tests are now version-independent and require no filesystem access.

---

## Post-fix verification

Unit test suite (`pytest tests/unit/ -q --no-cov`): **363 passed in 0.30s** — no regressions.

---

_Fixed: 2026-05-31T08:56:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
