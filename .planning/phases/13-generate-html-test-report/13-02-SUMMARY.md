---
phase: 13-generate-html-test-report
plan: 02
subsystem: testing
tags: [pytest, html-report, conftest, stash, fixtures, tdd, python]

# Dependency graph
requires:
  - phase: 13-01
    provides: build_step_table() in src/utils/html_report.py, HTML_REPORT_DIR and HTML_REPORT_DATE_FORMAT constants

provides:
  - tests/conftest.py — pytest_configure hook (tryfirst=True), _execution_summary_key StashKey, _video_path_key StashKey, workflow_report_extras fixture, extended pytest_runtest_makereport teardown branch
  - tests/unit/test_html_report_conftest.py — 15 unit tests covering HTML-10 through HTML-12

affects:
  - tests/smoke/ — smoke tests can now use workflow_report_extras fixture to inject ExecutionSummary into HTML report drill-down

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pytest_configure with tryfirst=True to set config.option.htmlpath before pytest-html reads it"
    - "StashKey pattern extended: _execution_summary_key and _video_path_key for cross-hook data flow"
    - "TDD RED/GREEN cycle: test file written first (13 failing), then conftest.py extended (15 passing)"
    - "rep.extras appended on teardown-phase report (pytest-html processes all phases)"
    - "config.getoption with skip=True to safely read --workflow before it may be registered"

key-files:
  created:
    - tests/unit/test_html_report_conftest.py
  modified:
    - tests/conftest.py
    - .gitignore

key-decisions:
  - "Do NOT set config.option.self_contained_html=True — relative screenshot links break in self-contained mode (RESEARCH.md Pitfall 3)"
  - "video_path stash set INSIDE if test_failed block — only stash when video is retained, not on pass (eliminates broken video links)"
  - "workflow_report_extras yields a _register callable — test calls it explicitly with summary; stash updated during test body before teardown hook runs"
  - "reports/assets/ added to .gitignore — pytest-html 4.x generates style.css there on every run"

patterns-established:
  - "Opt-in fixture pattern: yield a callable that tests call explicitly to register data; no autouse side effects"
  - "teardown-phase extras appending: list(getattr(rep, 'extras', []) or []) + [html_extras.html()] handles None and empty list"

requirements-completed: [HTML-10, HTML-11, HTML-12]

# Metrics
duration: 2min
completed: 2026-05-30
---

# Phase 13 Plan 02: Conftest pytest Integration Summary

**pytest integration wiring `pytest_configure` (tryfirst=True) for auto-timestamped HTML reports, `_execution_summary_key`/`_video_path_key` StashKeys, `workflow_report_extras` opt-in fixture, and teardown-phase extras attachment via `html_extras.html()` — 15 unit tests covering HTML-10 through HTML-12**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-31T03:04:40Z
- **Completed:** 2026-05-31T03:07:27Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Extended `tests/conftest.py` with 6 targeted additions (no existing lines removed or reordered)
- `pytest_configure` hook (tryfirst=True) sets `config.option.htmlpath` dynamically before pytest-html reads it — every test run produces a timestamped `reports/<name>_report_<YYYYMMDD_HHMMSS>.html` file
- `_execution_summary_key` and `_video_path_key` StashKeys declared at module level (HTML-10)
- `pytest_runtest_makereport` teardown branch attaches `build_step_table(summary)` and video link as `html_extras.html()` items on `rep.extras` (HTML-12)
- `workflow_report_extras` function-scoped opt-in fixture yields a `_register` callable (HTML-11)
- `video_recorder` teardown stashes `video_path` in `_video_path_key` on failure only
- 15 unit tests in TDD RED/GREEN cycle: 13 failing → all 15 passing
- Full unit suite: 324 tests passing (15 new + 309 existing), zero regressions
- `reports/assets/` added to `.gitignore` (pytest-html 4.x generates `style.css` there)

## Task Commits

Each task was committed atomically:

1. **TDD RED: add failing tests** - `3724e6e` (test)
2. **Task 1: Extend conftest.py** - `fff0bba` (feat)
3. **Deviation: gitignore reports/assets/** - `aada6a1` (chore)

**Plan metadata:** committed with docs(13-02) final commit

## Files Created/Modified
- `tests/conftest.py` — Added 6 additions: imports block, 2 StashKey declarations, pytest_configure hook, extended pytest_runtest_makereport, video_recorder stash line, workflow_report_extras fixture
- `tests/unit/test_html_report_conftest.py` — New: 15 tests in 5 classes covering HTML-10 through HTML-12
- `.gitignore` — Added `reports/assets/` (pytest-html 4.x generated artifact)

## Decisions Made
- Do NOT set `config.option.self_contained_html=True` — relative screenshot/video links in `FORMAT_HTML` extras are verbatim; self-contained mode does not rewrite them (RESEARCH.md Pitfall 3 confirmed)
- `video_path` stash is set only when test failed (`if test_failed`) — prevents the video link appearing in reports for passing tests where video was deleted
- `workflow_report_extras` yields a callable (`yield _register`) rather than returning one — aligns with generator fixture pattern; teardown no-ops cleanly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added reports/assets/ to .gitignore**
- **Found during:** Post-commit check — `reports/assets/style.css` appeared as untracked after running pytest-html
- **Issue:** pytest-html 4.x writes `reports/assets/style.css` on every run. This generated artifact was not gitignored.
- **Fix:** Added `reports/assets/` to `.gitignore` alongside the existing `reports/*.html` exclusion
- **Files modified:** `.gitignore`
- **Commit:** `aada6a1`

### TDD Gate Compliance

- RED gate: test file written first (`3724e6e`) — 13 tests failed (missing conftest attributes), 2 passed (hook presence tests that already worked)
- GREEN gate: conftest.py implemented (`fff0bba`) — all 15 tests pass
- REFACTOR gate: no refactoring needed — implementation was clean on first pass

## Issues Encountered
None beyond the gitignore deviation above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None — all fixtures and hooks are fully implemented. The `workflow_report_extras` fixture is opt-in; smoke tests need to request it explicitly to get drill-down tables in the HTML report.

## Threat Flags

All threats from the plan's threat model are addressed:

| Threat | File | Status |
|--------|------|--------|
| T-13-04: Tampering via workflow name from --workflow CLI arg | tests/conftest.py (pytest_configure) | Mitigated — safe_filename(Path(workflow_path).stem) applied before embedding in filename |
| T-13-05: Tampering via video_path filename in href | tests/conftest.py (makereport teardown) | Mitigated — Path(video_path).name extracts only the filename; relative href to videos/ only |
| T-13-06: Information disclosure — HTML report in reports/ | tests/conftest.py | Accepted — local dev tool, no network exposure |
| T-13-07: DoS via ensure_dir on every session | tests/conftest.py (pytest_configure) | Accepted — ensure_dir is idempotent (exist_ok=True) |

No new security-relevant surface introduced beyond what the plan's threat model covers.

## Self-Check: PASSED

---
*Phase: 13-generate-html-test-report*
*Completed: 2026-05-31*
