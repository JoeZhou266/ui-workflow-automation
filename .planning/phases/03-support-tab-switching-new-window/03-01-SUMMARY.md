---
phase: 03-support-tab-switching-new-window
plan: "01"
subsystem: core-enums, ui-base-page, unit-tests
tags: [enums, window-management, selenium, tdd, red-green]
dependency_graph:
  requires: []
  provides:
    - ActionType.SWITCH_TO_NEW_WINDOW
    - ActionType.SWITCH_TO_NEW_TAB
    - ActionType.SWITCH_TO_LATEST_WINDOW
    - BasePage.open_new_window
    - BasePage.switch_to_latest_window
  affects:
    - src/core/enums.py
    - src/ui/base_page.py
    - tests/unit/test_base_page_window.py
    - tests/unit/test_workflow_models.py
    - tests/unit/test_action_dispatch.py
tech_stack:
  added: []
  patterns:
    - EC.new_window_is_opened via WaitManager.wait_for (no sleep)
    - set-subtraction for new window handle detection
    - driver.switch_to.new_window atomic open+focus
key_files:
  created:
    - tests/unit/test_base_page_window.py
  modified:
    - src/core/enums.py
    - src/ui/base_page.py
    - tests/unit/test_workflow_models.py
    - tests/unit/test_action_dispatch.py
decisions:
  - "Append-only enum addition — NOOP unchanged, three new values at tail of ActionType"
  - "open_new_window is one Selenium call (switch_to.new_window is atomic open+switch)"
  - "switch_to_latest_window snapshots old_handles BEFORE wait, uses set subtraction (not [-1] index)"
  - "Three dispatch stubs left RED intentionally — Plan 03-02 wires element_actions.py dispatch"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-15"
  tasks_completed: 2
  files_changed: 5
---

# Phase 03 Plan 01: Window Action Schema and BasePage Primitives Summary

Three new `ActionType` enum values and two `BasePage` window management methods establish the contracts that Plan 03-02 consumes to wire the dispatch layer.

## What Was Built

### `src/core/enums.py` — Three new ActionType members

Appended after `NOOP = "noop"` (append-only, no reordering):

```python
SWITCH_TO_NEW_WINDOW = "switch_to_new_window"
SWITCH_TO_NEW_TAB = "switch_to_new_tab"
SWITCH_TO_LATEST_WINDOW = "switch_to_latest_window"
```

Pydantic automatically accepts `ElementDefinition(action="switch_to_new_window")` at JSON load time — no model schema change needed.

### `src/ui/base_page.py` — Two new interaction methods

**`open_new_window(type_hint: str = "window") -> None`**
- Single call: `self._driver.switch_to.new_window(type_hint)`
- `switch_to.new_window()` is atomic (opens AND focuses in one W3C command)
- No second `switch_to.window()` call — that would be a race condition

**`switch_to_latest_window(timeout: int = 10) -> None`**
- Snapshots `old_handles = set(self._driver.window_handles)` BEFORE the wait
- Waits via `self._wm.wait_for(EC.new_window_is_opened(list(old_handles)), ..., timeout=timeout)`
- Identifies new handle via `set(self._driver.window_handles) - old_handles` (not `[-1]` index)
- No `time.sleep()` — complies with CLAUDE.md synchronization constraint

## Test Results

```
pytest tests/unit/ -v
137 passed, 3 failed
```

| Test file | Result | Count |
|-----------|--------|-------|
| `test_base_page_window.py` | PASSED | 6 |
| `test_workflow_models.py::test_window_switch_action_types_are_valid` | PASSED | 1 |
| `test_action_dispatch.py::test_switch_to_new_window_action` | FAILED (expected RED) | 1 |
| `test_action_dispatch.py::test_switch_to_new_tab_action` | FAILED (expected RED) | 1 |
| `test_action_dispatch.py::test_switch_to_latest_window_action` | FAILED (expected RED) | 1 |
| All pre-existing tests | PASSED | 130 |

The 3 RED dispatch tests fail with `ElementActionError: Unhandled action 'switch_to_new_window/tab/latest_window'` — this is the expected TDD pre-condition for Plan 03-02.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | cd4a0d6 | feat(03-01): add SWITCH_TO_NEW_WINDOW, SWITCH_TO_NEW_TAB, SWITCH_TO_LATEST_WINDOW to ActionType |
| Task 2 | 812d57c | feat(03-01): add BasePage window methods and test suite (TDD RED/GREEN) |

## Deviations from Plan

None — plan executed exactly as written.

## Plan 03-02 Readiness

Plan 03-02 can immediately reference:
- `ActionType.SWITCH_TO_NEW_WINDOW`, `ActionType.SWITCH_TO_NEW_TAB`, `ActionType.SWITCH_TO_LATEST_WINDOW` from `src/core/enums.py`
- `BasePage.open_new_window(type_hint)` and `BasePage.switch_to_latest_window()` from `src/ui/base_page.py`
- The three RED dispatch tests in `test_action_dispatch.py::TestElementActions` that go GREEN when `element_actions.py` is wired

## Known Stubs

None — no placeholder data, hardcoded empty values, or TODO markers in shipped code.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. All changes are in-process (enum values, method calls on mocked driver). Threat model items T-03-02 and T-03-03 are mitigated:
- T-03-02: `switch_to_latest_window` uses `WaitManager.wait_for(timeout=10)` — no infinite loop, no `time.sleep`
- T-03-03: Handle identified by `set(window_handles) - old_handles` — not user input, not `[-1]` index

## Self-Check: PASSED

- `src/core/enums.py` contains three new ActionType values: VERIFIED
- `src/ui/base_page.py` contains `open_new_window` and `switch_to_latest_window`: VERIFIED
- `tests/unit/test_base_page_window.py` exists with 6 tests: VERIFIED
- `tests/unit/test_workflow_models.py` contains `test_window_switch_action_types_are_valid`: VERIFIED
- `tests/unit/test_action_dispatch.py` contains 3 RED stubs: VERIFIED
- Commit cd4a0d6 exists: VERIFIED
- Commit 812d57c exists: VERIFIED
