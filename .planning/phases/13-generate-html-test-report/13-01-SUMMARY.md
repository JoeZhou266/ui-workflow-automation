---
phase: 13-generate-html-test-report
plan: 01
subsystem: testing
tags: [pytest, html-report, selenium, python]

# Dependency graph
requires:
  - phase: 12-support-video-capture
    provides: StepResult and ExecutionSummary Pydantic models, constants pattern for reports/
  - phase: 09-support-last-day-of-month
    provides: ResultCollector, StepResult, ExecutionSummary in src/models/element_models.py

provides:
  - src/utils/html_report.py — pure transform layer: ExecutionSummary -> <details>/<summary> HTML block
  - src/core/constants.py — HTML_REPORT_DIR and HTML_REPORT_DATE_FORMAT constants
  - tests/unit/test_html_report.py — 25 unit tests covering HTML-01 through HTML-09
affects:
  - 13-02 — Plan 02 (pytest integration) imports build_step_table from src.utils.html_report

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "html.escape() applied to all StepResult string fields before embedding in HTML (XSS prevention)"
    - "Path.relative_to() for safe relative path computation from reports/ root"
    - "TDD RED/GREEN cycle: test file written and run (all failing), then implementation written"
    - "_STATUS_COLORS dict mapping StepStatus enum to Bootstrap-inspired hex color codes"

key-files:
  created:
    - src/utils/html_report.py
    - tests/unit/test_html_report.py
  modified:
    - src/core/constants.py

key-decisions:
  - "HTML_REPORT_DIR = 'reports' (not 'reports/html') — report HTML lives in reports/ root alongside screenshots/ and videos/ subdirectories"
  - "build_step_table() uses <details>/<summary> collapsible block — zero JS dependency, works in any HTML viewer"
  - "_relative_path() returns None for paths outside reports_dir — prevents path traversal in href/src attributes (T-13-02 mitigation)"
  - "All StepResult string fields html.escape()-d in both build_step_table() and _step_row_html() — covers T-13-01 threat"

patterns-established:
  - "Pure function pattern: html_report functions take data models as args, return HTML strings — no side effects"
  - "TDD inline imports: test factories use inline src imports to catch import errors early without polluting module-level namespace"

requirements-completed: [HTML-01, HTML-02, HTML-03, HTML-04, HTML-05, HTML-06, HTML-07, HTML-08, HTML-09]

# Metrics
duration: 2min
completed: 2026-05-30
---

# Phase 13 Plan 01: HTML Report Utility Summary

**Pure Python transform layer `html_report.py` converting `ExecutionSummary` to a self-contained `<details>/<summary>` HTML block with color-coded step rows, XSS prevention via `html.escape()`, and screenshot thumbnail links**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-30T23:00:00Z
- **Completed:** 2026-05-30T23:01:39Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Extended `src/core/constants.py` with `HTML_REPORT_DIR = "reports"` and `HTML_REPORT_DATE_FORMAT = "%Y%m%d_%H%M%S"`
- Implemented `src/utils/html_report.py` with `build_step_table()`, `_step_row_html()`, `_relative_path()` pure functions
- 25 unit tests written in TDD RED/GREEN cycle covering all 9 HTML requirement IDs
- Full unit test suite passes with 309 tests (25 new + 284 existing), zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add HTML report constants** - `1c45963` (feat)
2. **Task 2: Create html_report.py and test_html_report.py** - `4c6bb21` (feat)

**Plan metadata:** committed with docs(13-01) final commit

## Files Created/Modified
- `src/core/constants.py` - Added HTML_REPORT_DIR and HTML_REPORT_DATE_FORMAT constants after Video block
- `src/utils/html_report.py` - New pure-function module: build_step_table(), _step_row_html(), _relative_path()
- `tests/unit/test_html_report.py` - 25 unit tests in 9 test classes covering HTML-01 through HTML-09

## Decisions Made
- `HTML_REPORT_DIR = "reports"` (not `"reports/html"`) — report HTML lives in `reports/` root, consistent with the context decisions where screenshots and videos use `reports/<type>/` subdirs
- `<details>/<summary>` collapsible block chosen — no JavaScript dependency, works in any HTML viewer including pytest-html embedded extras
- `_relative_path()` returns `None` for paths outside `reports_dir` — safe path computation via `Path.relative_to()` ValueError catch
- FAILED step error cell uses `phase: {value}` format — exactly matches `test_passed_row_has_no_error_content` assertion pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None — all functions are fully implemented. `build_step_table()` reads real `ExecutionSummary.steps` list.

## Threat Flags

All threats from the plan's threat model are addressed:

| Threat | File | Status |
|--------|------|--------|
| T-13-01: XSS via StepResult string fields | src/utils/html_report.py | Mitigated — html.escape() on all string fields; verified by HTML-09 tests |
| T-13-02: Path traversal via screenshot_path | src/utils/html_report.py _relative_path() | Mitigated — Path.relative_to() raises ValueError outside reports_dir, returns None |

No new security-relevant surface introduced beyond what the plan's threat model covers.

## TDD Gate Compliance

- RED gate: test file written first, all 25 tests failed with `ModuleNotFoundError: No module named 'src.utils.html_report'`
- GREEN gate: implementation written, all 25 tests passed
- REFACTOR gate: no refactoring needed — implementation was clean on first pass

## Next Phase Readiness
- `src/utils/html_report.py` is ready for Plan 02 (pytest integration) to import `build_step_table`
- Constants `HTML_REPORT_DIR` and `HTML_REPORT_DATE_FORMAT` available for Plan 02 report file naming
- No blockers.

## Self-Check: PASSED

---
*Phase: 13-generate-html-test-report*
*Completed: 2026-05-30*
