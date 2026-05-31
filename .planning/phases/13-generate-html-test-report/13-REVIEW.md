---
phase: 13-generate-html-test-report
reviewed: 2026-05-30T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/utils/html_report.py
  - tests/unit/test_html_report.py
  - src/core/constants.py
  - tests/unit/test_html_report_conftest.py
  - tests/conftest.py
  - .gitignore
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-05-30T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the HTML test report feature: the `html_report.py` utility, its unit tests, the
`conftest.py` pytest hooks and fixtures, and supporting constants. The core `build_step_table`
and `_step_row_html` logic is correct and XSS-safe. The hook integration (`pytest_runtest_makereport`
as a tryfirst wrapper) follows the pytest-html recommended pattern. Three warnings and two info
items were found; no critical issues.

## Warnings

### WR-01: Hard top-level import of `pytest_html` breaks all test collection when package absent

**File:** `tests/conftest.py:10`
**Issue:** `from pytest_html import extras as html_extras` is an unconditional top-level import.
`conftest.py` is loaded at collection time for every pytest invocation, including pure unit tests
that have no need for HTML reporting. If `pytest-html` is absent (e.g. a stripped CI image, a
contributor who runs only `pip install selenium pytest`), the entire test suite fails at collection
with `ImportError` before any test runs — with a misleading error pointing at `conftest.py`
rather than the missing package.
**Fix:** Guard the import so unit tests can still run without `pytest-html`, or at minimum add
a clear error message:
```python
try:
    from pytest_html import extras as html_extras
    _PYTEST_HTML_AVAILABLE = True
except ImportError:
    html_extras = None
    _PYTEST_HTML_AVAILABLE = False
```
Then in the teardown branch of `pytest_runtest_makereport`:
```python
if _PYTEST_HTML_AVAILABLE and (summary is not None or video_path is not None):
    ...
    rep.extras = existing + [html_extras.html(html_str)]
```

---

### WR-02: `_relative_path` silently drops screenshot link when paths mix absolute and relative forms

**File:** `src/utils/html_report.py:106-123`
**Issue:** `Path(abs_path).relative_to(reports_dir)` raises `ValueError` — which is caught and
returns `None` — when `abs_path` and `reports_dir` are not in the same form (one absolute,
one relative). `ScreenshotManager.capture()` returns `str(file_path)` where `file_path` is a
`Path` built from the `base_dir` string `"reports/screenshots"`, so both are currently relative.
However, if a caller ever passes an absolute path (e.g. via `os.path.abspath` or by changing
`SCREENSHOT_DIR` to an absolute value), all screenshot links silently become empty cells with no
error or warning logged. The function contract says it returns `None` for outside paths, but the
drop is invisible to the caller.
**Fix:** Log a warning when `ValueError` is caught, so silent drops surface during debugging:
```python
def _relative_path(abs_path: str, reports_dir: str) -> Optional[str]:
    try:
        return str(Path(abs_path).relative_to(reports_dir))
    except ValueError:
        import logging
        logging.getLogger(__name__).debug(
            "_relative_path: %r is not under %r; screenshot link omitted",
            abs_path, reports_dir,
        )
        return None
```
Alternatively, resolve both paths before comparing to handle mixed absolute/relative:
```python
return str(Path(abs_path).resolve().relative_to(Path(reports_dir).resolve()))
```
Note: using `.resolve()` changes the security property — an absolute path outside the reports
tree would still raise `ValueError` and be caught correctly, so the path-traversal protection
is preserved.

---

### WR-03: `pytest_runtest_makereport` hook accumulates stash entries on every phase, but `_execution_summary_key` is only set by `workflow_report_extras` fixture which may not be requested — no guard for missing stash key race

**File:** `tests/conftest.py:63`
**Issue:** Line 63 calls `item.stash.setdefault(_phase_report_key, {})[rep.when] = rep`.
`pytest.Stash.setdefault` is documented and works correctly. However, the `_execution_summary_key`
stash value is only written by the opt-in `workflow_report_extras` fixture (line 219). If a test
requests `video_recorder` but NOT `workflow_report_extras`, `item.stash.get(_execution_summary_key, None)`
correctly returns `None` (line 67). This is fine.

The real concern is on line 79:
```python
existing = list(getattr(rep, 'extras', []) or [])
```
`rep.extras` is a `pytest_html` attribute. When `pytest-html` is not installed, `rep` is a plain
`pytest.CollectReport` or `TestReport` with no `.extras` attribute — `getattr` returns `[]`, which
is correct. But when `pytest-html` IS installed, `rep.extras` is initialized to `[]` by pytest-html.
The `or []` guard means that if `rep.extras` is somehow falsy (e.g. `None`), existing becomes `[]`
and previously attached extras are silently discarded.

The `or []` branch will never trigger with pytest-html installed (extras is always a list), but it
could mask a configuration issue where another plugin sets `rep.extras = None`.
**Fix:** Be explicit about the None case:
```python
existing = list(rep.extras) if getattr(rep, "extras", None) is not None else []
```

## Info

### IN-01: `test_makereport_source_contains_teardown_branch` inspects source text — brittle assertion

**File:** `tests/unit/test_html_report_conftest.py:128-140`
**Issue:** The test uses `inspect.getsource()` and asserts that literal strings `"teardown"`,
`"build_step_table"`, and `"html_extras"` appear in the source. Any refactoring that renames a
local variable or extracts a helper function would break this test without changing the observable
behavior. Source-text inspection is an anti-pattern for behavioral testing.
**Fix:** Replace the source-inspection test with a behavioral test. Create a lightweight mock
`item` with a fake stash, call `pytest_runtest_makereport` with `when="teardown"`, and assert
that `rep.extras` is populated. This is admittedly more complex, but eliminates the brittleness.
As a minimal improvement, at least document the intent:
```python
def test_makereport_source_contains_teardown_branch(self):
    """Source inspection: verifies teardown logic exists. Replace with behavioral test when
    pytest mock infrastructure is available."""
    ...
```

---

### IN-02: `_step_row_html` silently omits error details for SKIPPED steps that carry an error message

**File:** `src/utils/html_report.py:75-79`
**Issue:** The `error_cell` is only populated when `step.status == StepStatus.FAILED`.
If a SKIPPED step has `error_message` set (e.g. a conditional skip with a reason stored in the
field), that message is silently dropped and the `Error / Phase` cell renders blank. The current
`StepStatus` domain does not explicitly require SKIPPED steps to have a null `error_message`, so
this is a plausible data state.
**Fix:** Extend the condition to render error details for skipped steps as well:
```python
if step.status in (StepStatus.FAILED, StepStatus.SKIPPED) and step.error_message:
    err = escape(step.error_message or "")
    phase = escape(str(step.failure_phase.value if step.failure_phase else ""))
    error_cell = f"{err}<br><small>phase: {phase}</small>"
```
Alternatively, if SKIPPED steps are never expected to carry `error_message`, add an assertion or
validator to `StepResult` to enforce that invariant.

---

_Reviewed: 2026-05-30T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
