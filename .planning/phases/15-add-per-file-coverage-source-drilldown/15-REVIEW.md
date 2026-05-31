---
phase: 15-add-per-file-coverage-source-drilldown
reviewed: 2026-05-31T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - .coveragerc
  - src/core/constants.py
  - src/utils/coverage_index.py
  - tests/unit/test_coverage_index.py
  - tests/conftest.py
  - tests/unit/test_coverage_conftest.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2026-05-31
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the Phase 15 additions: `.coveragerc`, `src/core/constants.py`, `src/utils/coverage_index.py`, `tests/conftest.py`, and two unit test files. The implementation is well-structured with good fail-open handling at the session hook level. No critical issues were found. Four warnings were identified: a negative percentage logic edge case, non-deterministic CSS file selection, a hard-coded `.coverage` path guard inconsistency, and a test making an undocumented version-specific runtime assumption about coverage.py behavior. Three info-level items cover a lazy `warnings` import, an undocumented internal API, and a weak assertion in test code.

## Warnings

### WR-01: Negative overall coverage percentage when miss > stmts

**File:** `src/utils/coverage_index.py:75`
**Issue:** `overall_pct = round((1 - total_miss / total_stmts) * 100) if total_stmts else 0` produces a negative integer when `total_miss > total_stmts`. This can occur with corrupted `.coverage` data or when coverage.py reports partial-branch counts that inflate `n_missing`. The negative value is silently rendered into HTML with no clamping or validation.
**Fix:**
```python
# Clamp to [0, 100] to avoid rendering negative coverage percentages
raw_pct = round((1 - total_miss / total_stmts) * 100) if total_stmts else 0
overall_pct = max(0, min(100, raw_pct))
```
Apply the same clamp to `pkg_pct` in `_render_package()` at line 124 for consistency.

---

### WR-02: Non-deterministic CSS file selection when multiple style_cb_*.css files exist

**File:** `src/utils/coverage_index.py:47-48`
**Issue:** `css_files = glob.glob(...)` returns results in filesystem order (OS-dependent, not alphabetically sorted). `css_files[0]` silently picks an arbitrary file if multiple `style_cb_*.css` files are present (e.g., stale CSS from a previous coverage version). On macOS HFS+ this may appear stable; on Linux ext4 it is not.
**Fix:**
```python
css_files = sorted(glob.glob(os.path.join(coverage_dir, "style_cb_*.css")))
css_href = os.path.basename(css_files[-1]) if css_files else ""
```
Sort ascending and take the last (newest hash) to be deterministic. Alternatively, take `css_files[0]` after sorting — either way, the key fix is the `sorted()` call.

---

### WR-03: `.coverage` path guard in conftest does not match configurable data_file

**File:** `tests/conftest.py:107`
**Issue:** The guard `if not Path(".coverage").exists(): return` hard-codes `.coverage` as the expected binary file path. `build_custom_index()` also defaults to `".coverage"` — so they agree under the default configuration. However, if the project or CI sets `COVERAGE_FILE` environment variable or configures `[run] data_file` in `.coveragerc`, the binary is written to a different path. The guard would then skip generation even though the data file exists, causing the custom index to be silently omitted without any warning.
**Fix:**
```python
# Read the data file path the same way coverage.py resolves it
import coverage as _cov_mod
_data_file = _cov_mod.Coverage().config.data_file  # respects COVERAGE_FILE env + .coveragerc
if not Path(_data_file).exists():
    return
# pass data_file to build_custom_index so both use the same path
html = build_custom_index(coverage_dir=COVERAGE_DIR, data_file=_data_file)
```
If the project always uses the default `.coverage` path (as `.coveragerc` does not set `data_file`), this is low risk in practice but worth hardening.

---

### WR-04: Missing `.coverage` test uses real coverage.py with undocumented version assumption

**File:** `tests/unit/test_coverage_index.py:267-288`
**Issue:** `TestMissingCoverageFile.test_returns_valid_html_on_missing_data_file` and `test_no_crash_on_missing_data_file` call `build_custom_index()` without a `_cov_factory`, causing them to instantiate a real `coverage.Coverage` object against a nonexistent file path. The tests rely on coverage.py 7.x behavior (returns empty data, no exception). The docstring in the test class documents this, but if the project ever upgrades to a coverage.py version that raises `NoDataError`, both tests fail for the wrong reason — the test harness shows a conftest import error rather than an assertion failure, making the regression hard to diagnose.
**Fix:** Inject a mock factory that simulates the empty-data case, making the test version-independent and faster:
```python
def test_returns_valid_html_on_missing_data_file(self):
    from src.utils.coverage_index import build_custom_index

    def empty_factory(data_file=".coverage"):
        cov = MagicMock()
        cov.get_data.return_value.measured_files.return_value = []
        return cov

    with tempfile.TemporaryDirectory() as tmpdir:
        html = build_custom_index(coverage_dir=tmpdir, _cov_factory=empty_factory)
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
```

---

## Info

### IN-01: `import warnings` inside except block — should be at module level

**File:** `tests/conftest.py:115`
**Issue:** `import warnings` is placed inside the `except Exception` block. Python caches imports in `sys.modules`, so this is not a performance problem in practice. However, it deviates from PEP 8's convention of placing all imports at the top of the module and could be missed during a dependency audit. `warnings` is a stdlib module and incurs no risk — this is purely a style inconsistency with the rest of the file's imports.
**Fix:** Move `import warnings` to the top-level import section (after `import os`, before `import pytest`).

---

### IN-02: `coverage.files.flat_rootname` is an undocumented internal API — not called out in docstring

**File:** `src/utils/coverage_index.py:3,61`
**Issue:** The module docstring for `build_custom_index()` correctly warns about `cov._analyze()` being internal. However, `from coverage.files import flat_rootname` (line 3, used on line 61) is also an undocumented internal — it is not part of coverage.py's public API surface. Both are treated the same by the try/except in `pytest_sessionfinish`, but the docstring omits this second internal dependency, leaving a maintenance gap for future readers.
**Fix:** Extend the docstring warning:
```python
WARNING: Uses coverage._analyze() and coverage.files.flat_rootname, both internal
APIs. Stable across coverage.py 5.x-7.x but may break in a future major version.
Wrapped in try/except at the call site (pytest_sessionfinish) to fail-open.
```

---

### IN-03: `test_sessionfinish_uses_getattr_for_no_cov` assertion is overly broad

**File:** `tests/unit/test_coverage_conftest.py:83-88`
**Issue:** The test checks `assert "getattr" in src` to verify that `getattr(config.option, 'no_cov', False)` is used. This passes if `getattr` appears anywhere in `pytest_sessionfinish`'s source for any reason. If the implementation is refactored to access `no_cov` directly (e.g., `config.option.no_cov`) and `getattr` remains in source for a different reason, the test gives a false pass.
**Fix:** Tighten the assertion to check for the specific safe-access pattern:
```python
assert "getattr(config.option, 'no_cov'" in src or \
       'getattr(config.option, "no_cov"' in src, (
    "pytest_sessionfinish should use getattr(config.option, 'no_cov', False)"
)
```

---

_Reviewed: 2026-05-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
