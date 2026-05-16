---
phase: 03-support-tab-switching-new-window
plan: "02"
subsystem: actions-dispatch, testdata
tags: [dispatch, window-management, selenium, tdd, green, json-fixture]
dependency_graph:
  requires:
    - 03-01 (ActionType enum values, BasePage.open_new_window, BasePage.switch_to_latest_window)
  provides:
    - ElementActions dispatch for SWITCH_TO_NEW_WINDOW
    - ElementActions dispatch for SWITCH_TO_NEW_TAB
    - ElementActions dispatch for SWITCH_TO_LATEST_WINDOW
    - testdata/workflows/tabs/new_window_tab.json fixture
  affects:
    - src/actions/element_actions.py
    - testdata/workflows/tabs/new_window_tab.json
tech_stack:
  added: []
  patterns:
    - Sentinel locator pattern for locator-free actions (Option A from RESEARCH.md)
    - Single-line elif dispatch branches (no helper method)
    - workflow_name field required in WorkflowDefinition (not "name")
key_files:
  created:
    - testdata/workflows/tabs/new_window_tab.json
  modified:
    - src/actions/element_actions.py
decisions:
  - "Three elif branches inserted after UPLOAD and before else raise — no helper method added"
  - "Window-switch branches pass no element.locator or element.name — sentinel locator ignored at dispatch"
  - "SWITCH_TO_LATEST_WINDOW calls switch_to_latest_window() with no args — uses default timeout=10"
  - "JSON fixture uses workflow_name field (not name) per WorkflowDefinition model schema"
  - "Sentinel locator value _window satisfies required LocatorDefinition field without model change"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-15"
  tasks_completed: 2
  files_changed: 2
---

# Phase 03 Plan 02: Window-Switch Dispatch Wiring and JSON Fixture Summary

Three `elif` branches wired into `ElementActions.execute()` transition the three RED dispatch tests from Plan 03-01 to GREEN, completing the TDD cycle. A `testdata/workflows/tabs/new_window_tab.json` fixture demonstrates the end-to-end JSON declaration pattern using the sentinel locator approach.

## What Was Built

### `src/actions/element_actions.py` — Three new dispatch branches

Inserted after the `UPLOAD` branch (line 76) and before the `else: raise ElementActionError` fallback:

```python
elif action == ActionType.SWITCH_TO_NEW_WINDOW:
    self._page.open_new_window("window")

elif action == ActionType.SWITCH_TO_NEW_TAB:
    self._page.open_new_window("tab")

elif action == ActionType.SWITCH_TO_LATEST_WINDOW:
    self._page.switch_to_latest_window()
```

Final dispatch chain order: `INPUT → CLICK → SELECT_BY_TEXT → SELECT_BY_VALUE → SELECT_BY_INDEX → CHECK → UNCHECK → SELECT_RADIO → UPLOAD → SWITCH_TO_NEW_WINDOW → SWITCH_TO_NEW_TAB → SWITCH_TO_LATEST_WINDOW → else raise`

Key design decisions:
- `type_hint` values (`"window"`, `"tab"`) are hardcoded string literals — not derived from any JSON field. Mitigates T-03-06 (Elevation of Privilege).
- No `element.locator` or `element.name` passed to window-switch branches — the sentinel locator in JSON is ignored at dispatch (RESEARCH.md Pattern 5, Option A).
- No helper method added — one-line bodies match `CHECK`/`UNCHECK`/`SELECT_RADIO` convention.
- No new imports — `ActionType` was already imported at line 5; `BasePage` methods resolve at runtime via `self._page`.

### `testdata/workflows/tabs/new_window_tab.json` — Workflow JSON fixture

A valid `WorkflowDefinition` with all three window-switch action types declared using the sentinel locator pattern:

```
Open New Window: switch_to_new_window   (locator: {by: id, value: _window})
Open New Tab: switch_to_new_tab         (locator: {by: id, value: _window})
Switch To Latest Window: switch_to_latest_window  (locator: {by: id, value: _window})
```

Uses `workflow_name` field (not `name`) per `WorkflowDefinition` schema. `start_url: "about:blank"` avoids real URL dependency for the unit-level fixture.

## Test Results

```
pytest tests/unit/ -v
140 passed in 0.21s
```

Delta from Phase 2 baseline (130 tests): +10 tests total across Phase 3
- +3 dispatch tests (Plan 03-02, RED→GREEN): `test_switch_to_new_window_action`, `test_switch_to_new_tab_action`, `test_switch_to_latest_window_action`
- +6 BasePage window tests (Plan 03-01): `test_base_page_window.py`
- +1 model test (Plan 03-01): `test_window_switch_action_types_are_valid`

### Phase 3 Success Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|---------|
| SC-1: SWITCH_TO_NEW_WINDOW and SWITCH_TO_NEW_TAB accept JSON declaration | GREEN | `test_window_switch_action_types_are_valid` PASSED; `test_switch_to_new_window_action` + `test_switch_to_new_tab_action` PASSED |
| SC-2: `open_new_window("window")` calls `driver.switch_to.new_window("window")` atomically | GREEN | `TestOpenNewWindow` (6 tests) in `test_base_page_window.py` PASSED |
| SC-3: Driver focus shifts globally — subsequent elements use `self._driver` in new window context | GREEN | Driver state is global on WebDriver instance; verified by RESEARCH.md Pattern 4 analysis + dispatch routing tests |
| SC-4: Unit tests cover dispatch, window methods, and enum membership | GREEN | 10 new tests total: 3 dispatch + 6 window + 1 model |

All four Phase 3 success criteria are GREEN.

### WorkflowLoader.load() output for new_window_tab.json

```
Open New Window: switch_to_new_window
Open New Tab: switch_to_new_tab
Switch To Latest Window: switch_to_latest_window
OK — 3 window-switch elements loaded and validated
```

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 87eb939 | feat(03-02): add SWITCH_TO_NEW_WINDOW, SWITCH_TO_NEW_TAB, SWITCH_TO_LATEST_WINDOW dispatch branches |
| Task 2 | ffef8c4 | feat(03-02): add new_window_tab.json workflow fixture for window-switch actions |

## Deviations from Plan

**1. [Rule 1 - Bug] Corrected WorkflowDefinition field name in JSON fixture**
- **Found during:** Task 2 verification
- **Issue:** Plan template used `"name"` as the top-level field in the JSON fixture, but `WorkflowDefinition` requires `"workflow_name"` (Pydantic validation error: `Field required [workflow_name]`)
- **Fix:** Changed top-level key from `"name"` to `"workflow_name"` in `new_window_tab.json`
- **Files modified:** `testdata/workflows/tabs/new_window_tab.json`
- **Commit:** ffef8c4 (included in Task 2 commit)

## Known Stubs

None — no placeholder data, hardcoded empty values, or TODO markers in shipped code.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. Threat model items from Plan 03-02 threat register are mitigated:
- T-03-05: Dispatch branches only reachable after Pydantic enum validation; `else: raise ElementActionError` fallback remains LAST and present.
- T-03-06: `type_hint` values are hardcoded literals in dispatch branches — not derived from JSON input.
- T-03-07: Accepted — `switch_to_latest_window()` timeout mitigated at BasePage layer (T-03-02).
- T-03-08: Accepted — `new_window_tab.json` is testdata only; no production execution path.

## Self-Check: PASSED

- `src/actions/element_actions.py` contains three new elif branches after UPLOAD and before else: VERIFIED
- `self._page.open_new_window("window")` exists in dispatch: VERIFIED
- `self._page.open_new_window("tab")` exists in dispatch: VERIFIED
- `self._page.switch_to_latest_window()` exists in dispatch: VERIFIED
- `testdata/workflows/tabs/new_window_tab.json` exists and passes WorkflowLoader validation: VERIFIED
- All 140 unit tests pass (0 failures): VERIFIED
- Commit 87eb939 exists: VERIFIED
- Commit ffef8c4 exists: VERIFIED
