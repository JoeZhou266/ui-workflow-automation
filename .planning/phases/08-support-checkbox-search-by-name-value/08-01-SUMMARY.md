---
phase: "08"
plan: "01"
subsystem: "actions/ui"
tags: ["checkbox", "css-selector", "tdd", "value-disambiguation"]
dependency_graph:
  requires: []
  provides: ["BasePage.check(value)", "BasePage.uncheck(value)", "ElementActions CHECK/UNCHECK value passthrough"]
  affects: ["src/ui/base_page.py", "src/actions/element_actions.py"]
tech_stack:
  added: []
  patterns: ["CSS selector fork (mirrors select_radio pattern)"]
key_files:
  created: []
  modified:
    - src/ui/base_page.py
    - src/actions/element_actions.py
    - tests/unit/test_action_dispatch.py
decisions:
  - "Mirror select_radio pattern exactly (type='checkbox' instead of type='radio') — no new mechanism needed"
  - "Update _make_element() helper to accept locator kwarg override for new test cases"
metrics:
  duration: "3 minutes"
  completed_date: "2026-05-27"
  tasks_completed: 2
  files_modified: 3
---

# Phase 08 Plan 01: Support Checkbox Search by Name+Value Summary

**One-liner:** Transparent CHECK/UNCHECK value disambiguation via CSS selector fork `input[type="checkbox"][name="..."][value="..."]` — mirrors select_radio pattern exactly.

## What Was Built

Extended `BasePage.check()` and `BasePage.uncheck()` with an optional `value: str = ""` parameter. When `value` is non-empty and `locator.by == "name"`, the methods build a targeted CSS selector `input[type="checkbox"][name="..."][value="..."]` to locate the exact checkbox among multiple grouped checkboxes sharing the same name attribute. Otherwise, the original locator is used unchanged (fully backwards compatible).

Updated `ElementActions.execute()` CHECK and UNCHECK branches to pass the resolved value through as the third argument — identical to the existing SELECT_RADIO passthrough pattern.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | e88e869 | PASSED — 4 new tests failed as expected |
| GREEN (feat commit) | 046cedc | PASSED — all 4 tests pass, 34/34 suite passes |

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RED: Write failing tests and update existing dispatch assertions | e88e869 | tests/unit/test_action_dispatch.py |
| 2 | GREEN: Extend BasePage.check/uncheck and wire value passthrough | 046cedc | src/ui/base_page.py, src/actions/element_actions.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated `_make_element()` to support `locator` kwarg override**
- **Found during:** Task 1
- **Issue:** The test helper `_make_element()` always set `locator=_make_locator()` as a positional keyword argument before `**kwargs`, preventing callers from overriding the locator via `locator=...` kwarg (would cause `TypeError: got multiple values for keyword argument 'locator'`).
- **Fix:** Added explicit `locator: LocatorDefinition | None = None` parameter to `_make_element()` and used `locator if locator is not None else _make_locator()` internally. This enabled `test_check_dispatch_passes_value` to pass `locator=_make_locator(by="name", value="hobby")` correctly.
- **Files modified:** tests/unit/test_action_dispatch.py
- **Commit:** e88e869

## Known Stubs

None — all functionality is fully implemented and tested.

## Threat Flags

No new security surface introduced. The CSS selector interpolation uses developer-authored workflow JSON values (validated by Pydantic at load time). See plan's threat model: T-08-01 (accept), T-08-02 (accept).

## Deferred Items

5 pre-existing failures in `tests/unit/test_value_resolver.py` (`TestGenerators::test_sin_length`, `test_sin_first_digit`, `test_sin_luhn_valid`, `TestPlaceholderRegistry::test_resolve_sin_number`, `TestValueResolverIntegration::test_resolver_expands_sin`) — unrelated to this plan's changes. These existed before this plan and are out of scope.

## Self-Check

Files exist:
- src/ui/base_page.py: FOUND (modified)
- src/actions/element_actions.py: FOUND (modified)
- tests/unit/test_action_dispatch.py: FOUND (modified)

Commits exist:
- e88e869: FOUND (test RED commit)
- 046cedc: FOUND (feat GREEN commit)

## Self-Check: PASSED
