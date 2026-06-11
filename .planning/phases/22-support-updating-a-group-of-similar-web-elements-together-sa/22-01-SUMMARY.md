---
phase: 22-support-updating-a-group-of-similar-web-elements-together-sa
plan: 01
subsystem: testing
tags: [pytest, pydantic, selenium, index-range, tdd, wave0]

# Dependency graph
requires:
  - phase: 21-support-locator-value-from-workflow-parameters-e-g-locator-v
    provides: partial/embedded ${param} expansion in locator.value (Phase 21 seam)
  - phase: 17-support-parameter-value-expansion
    provides: anchored ${param} expansion in element values and params plumbing
provides:
  - RED test matrix for Phase 22 index_range expansion (Wave 0 contract)
  - TestIndexRange class (5 methods) covering D-01, D-02b, D-02c Pydantic validation
  - TestReservedParamName class (3 methods) covering reserved 'index' param at load time
  - TestIndexExpansion class (10 methods) covering D-02a, D-03, D-03b, D-04, D-05, D-07, D-08, D-09, D-09b, no-regression
affects:
  - 22-02-PLAN.md (Wave 1 implementation must make these tests GREEN)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 RED-test-first: write failing tests before implementation (Nyquist contract)"
    - "Engine-level test isolation: _run_section called directly with DynamicSection patched"
    - "ActionFactory.run patched at module path to intercept per-index calls without browser"

key-files:
  created:
    - tests/unit/test_index_expansion.py
  modified:
    - tests/unit/test_workflow_models.py
    - tests/unit/test_json_loader.py

key-decisions:
  - "TestIndexExpansion calls _run_section directly, not engine.run(), to avoid Navigator/page-load deps"
  - "ActionFactory.run patched at 'src.actions.action_factory.ActionFactory.run' (module path); DynamicSection patched in workflow_engine to avoid section instantiation"
  - "test_non_indexed_element_unchanged is GREEN immediately — existing code already handles plain elements correctly (no-regression baseline)"
  - "test_non_reserved_param_accepted is GREEN immediately — non-index params already accepted; the test guards positive path for Plan 02"

patterns-established:
  - "Pattern: Engine-level loop expansion tests — patch ActionFactory.run with side_effect list, capture concrete elements via closure, assert on _collector.summary().steps"

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-07, D-08, D-09, reserved, no-regression]

# Metrics
duration: 32min
completed: 2026-06-11
---

# Phase 22 Plan 01: Wave 0 RED test matrix for index_range loop expansion

**Full Nyquist test contract for index_range expansion: 18 tests across 3 classes covering all of D-01..D-09, reserved-name guard, and no-regression — all RED because implementation is absent (Wave 0)**

## Performance

- **Duration:** ~32 min
- **Started:** 2026-06-11T14:10:00Z
- **Completed:** 2026-06-11T14:42:11Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Established the full Wave 0 test contract for Phase 22 index_range expansion: 18 tests, all correctly RED
- TestIndexRange (5 methods in test_workflow_models.py) locks D-01 default-None, D-02b start>end validation, D-02c length-not-2 validation, plus two positive guards
- TestReservedParamName (3 methods in test_json_loader.py) enforces reserved 'index' name rejection at both WorkflowLoader.load and WorkflowLoader.load_raw entry points
- TestIndexExpansion (10 methods in test_index_expansion.py) covers full engine-level behavior: loop call count, ${index} substitution in name/locator/XPath, concrete StepResult names, same-value-all-indices, N-results, fail-continue, skip-vs-fail, no-regression
- No browser required; no src/ files modified; existing test suite unaffected (34 action dispatch tests pass)

## Task Commits

1. **Task 1: TestIndexRange + TestReservedParamName RED tests** - `8a090d3` (test)
2. **Task 2: TestIndexExpansion engine-level RED tests** - `79335ec` (test)

## Files Created/Modified

- `tests/unit/test_index_expansion.py` — New file: TestIndexExpansion class with 10 methods driving WorkflowEngine._run_section directly with patched ActionFactory and real ResultCollector
- `tests/unit/test_workflow_models.py` — Appended TestIndexRange class with 5 methods for Pydantic index_range field validation
- `tests/unit/test_json_loader.py` — Appended TestReservedParamName class with 3 methods for reserved 'index' parameter enforcement

## Decisions Made

- Called `_run_section` directly rather than `engine.run()` to avoid Navigator, page-load, and browser-navigation dependencies; this gives clean, fast, no-browser unit tests
- Patched `src.actions.action_factory.ActionFactory.run` (not a method on a live instance) plus `src.workflow.workflow_engine.DynamicSection` so `_run_element`'s real try/except logic executes correctly without Selenium
- Used `side_effect` lists with `[None, ElementActionError(...), None, ...]` pattern (from test_action_dispatch.py analog) to sequence multi-index outcomes precisely
- The two GREEN tests (`test_non_indexed_element_unchanged`, `test_non_reserved_param_accepted`) are intentional: they verify existing behavior is preserved and provide immediate confidence that the test infrastructure itself is sound

## Deviations from Plan

None — plan executed exactly as written. Test method names match VALIDATION.md command table exactly. No production src/ files modified.

## Issues Encountered

None. `_make_engine()` required patching WaitManager, ScreenshotManager, BasePage, and Navigator construction to avoid real Selenium deps; used nested context managers. All engine-level tests collected cleanly without import errors.

## Known Stubs

None — this plan creates test files only; no UI rendering or data sources involved.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This plan writes test files only.

## Next Phase Readiness

- Wave 0 complete: all three test artifacts exist with exact class/method names from VALIDATION.md
- Plan 02 (Wave 1) can now implement: `index_range` field on ElementDefinition + Pydantic validator, `${index}` substitution in `_run_section` loop, reserved-name guard in WorkflowLoader
- The 16 RED tests become the acceptance gate for Plan 02 — implementation is complete when all 16 pass without modifying the test files
- Existing 417 unit tests unaffected; `test_action_dispatch.py` baseline confirmed (34 passed)

---
*Phase: 22-support-updating-a-group-of-similar-web-elements-together-sa*
*Completed: 2026-06-11*
