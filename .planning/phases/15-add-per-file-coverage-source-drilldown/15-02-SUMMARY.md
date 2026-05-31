---
phase: 15-add-per-file-coverage-source-drilldown
plan: "02"
subsystem: coverage
tags: [coverage, pytest-hooks, conftest, html-report, unit-tests]
dependency_graph:
  requires:
    - build_custom_index() pure function in src/utils/coverage_index.py (plan 01)
    - COVERAGE_DIR constant in src/core/constants.py (plan 01)
  provides:
    - pytest_sessionfinish hook in tests/conftest.py
    - conditional coverage link in pytest_runtest_makereport teardown extras
    - COV-07, COV-08, COV-09 unit test suite
  affects:
    - reports/coverage/custom_index.html (generated on every pytest run with coverage)
    - pytest HTML report (coverage link appended to each test's extras when index exists)
tech_stack:
  added: []
  patterns:
    - pytest hook pattern (plain function, not wrapper) for pytest_sessionfinish
    - Fail-open exception handling with warnings.warn (never fail the session)
    - Conditional HTML extras injection in pytest_runtest_makereport teardown
    - inspect.getsource() assertions in unit tests (mirrors test_html_report_conftest.py)
key_files:
  created:
    - tests/unit/test_coverage_conftest.py
  modified:
    - tests/conftest.py
decisions:
  - "Guard teardown extras block also fires when coverage_index.exists() — widened from (summary or video_path) to (summary or video_path or coverage_index.exists()) so coverage link appears even in runs without workflow summaries or video"
  - "import warnings inside except block (not at module top) — matches existing pattern in coverage_index.py and avoids polluting conftest module namespace"
metrics:
  duration: "101s"
  completed: "2026-05-31T04:47:16Z"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  tests_added: 14
  tests_total: 363
---

# Phase 15 Plan 02: Conftest Hooks and Coverage Link Integration Summary

`pytest_sessionfinish` hook added to `tests/conftest.py` calling `build_custom_index()` with `--no-cov` and `.coverage`-existence guards plus fail-open exception handler; `pytest_runtest_makereport` teardown extended with conditional `coverage/index.html` link; 14 unit tests (COV-07, COV-08, COV-09) verify all additions with 363 total passing and zero regressions.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Extend conftest.py with pytest_sessionfinish hook and coverage link | 3e327a1 | tests/conftest.py |
| 2 | Create test_coverage_conftest.py for COV-07, COV-08, COV-09 | 2c910b4 | tests/unit/test_coverage_conftest.py |

## Verification Results

- `python3 -c "import tests.conftest as c; assert hasattr(c, 'pytest_sessionfinish'); assert callable(c.pytest_sessionfinish)"`: PASS
- `inspect.getsource(pytest_sessionfinish)` contains `no_cov` and `build_custom_index`: PASS
- `inspect.getsource(pytest_runtest_makereport)` contains `coverage/index.html`: PASS
- `pytest tests/unit/test_coverage_conftest.py -v --no-cov`: 14 passed
- `pytest tests/unit/ -v --no-cov`: 363 passed (0 regressions vs Plan 01 baseline of 349)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The hook generates real output when `.coverage` exists; the coverage link renders when `reports/coverage/index.html` exists.

## Threat Surface Scan

No new trust boundaries beyond the plan's `<threat_model>`:
- T-15-04 (DoS via build_custom_index failure): mitigated — `try/except Exception` + `warnings.warn` in place
- T-15-05 (Injection via coverage link HTML): accepted — hardcoded literal, no dynamic content
- T-15-06 (Information disclosure in custom_index.html): accepted — local tool, reports/ gitignored

## Self-Check: PASSED

- `tests/conftest.py` modified with pytest_sessionfinish and coverage link: FOUND
- `tests/unit/test_coverage_conftest.py` created with TestSessionFinishHook, TestNoCovDetection, TestCoverageLinkExtras: FOUND
- Commit 3e327a1 exists: FOUND
- Commit 2c910b4 exists: FOUND
