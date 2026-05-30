# Roadmap: UI Workflow Automation

## Overview

Data-driven Selenium automation framework that reads workflow definitions from JSON and executes browser interactions across a hierarchy of Workflow → Tabs → Pages → Sections → Elements. Phases extend the framework's capabilities incrementally.

## Phases

- [x] **Phase 1: Support Nested JSON** - `$ref` file-reference resolution in workflow loader
- [x] **Phase 2: Support More Web Elements** - checkBox, radio, number, email element actions
- [x] **Phase 3: Support Tab Switching and New Window Focus** - switch tab / new window via workflow JSON
- [x] **Phase 4: Support Dynamic Placeholder Expansion** - registry-based ${placeholder} expansion in workflow JSON values
- [x] **Phase 5: Support wait_seconds in WaitConditionType** - fixed-duration pause in pre_wait/post_wait via a `wait_seconds` condition reusing the existing `timeout` field
- [x] **Phase 6: Support execute_js_script Action Type** - execute arbitrary JavaScript from workflow JSON via `element.value` field
- [x] **Phase 7: Support skip-if-not-visible** - SkipElementSignal exception + ActionFactory visibility probe + WorkflowEngine catch, records step as SKIPPED not FAILED
- [x] **Phase 8: Support checkbox search by name+value** - transparent enhancement to CHECK/UNCHECK via CSS selector (mirrors select_radio pattern)
- [x] **Phase 9: Support last-day-of-month placeholder** - `${last_day_of_month}` generator returning MM/DD/YYYY of the last calendar day of the current month
- [x] **Phase 10: Support ${env:KEY} config placeholder** - `${env:KEY}` namespace resolving to env YAML config values so account numbers, credentials, and env-specific IDs live in config rather than workflow JSON (completed 2026-05-30)

## Phase Details

### Phase 1: Support Nested JSON
**Goal**: Enable `$ref` file references in workflow JSON so shared tabs/pages/sections can be reused across workflows
**Depends on**: Nothing (first phase)
**Success Criteria** (what must be TRUE):
  1. `resolve_refs()` recursively resolves `$ref` nodes in workflow JSON
  2. Circular reference detection raises `ValueError`
  3. Existing smoke tests pass with `$ref`-based sample workflows
**Plans**: Complete

Plans:
- [x] 01-01: Implement `resolve_refs` and wire into `WorkflowLoader`
- [x] 01-02: Refactor sample workflows to use `$ref` file references

### Phase 2: Support More Web Elements
**Goal**: Add action dispatch for checkBox, radio, number, and email input types in `element_actions.py`
**Depends on**: Phase 1
**Success Criteria** (what must be TRUE):
  1. Checkbox elements can be checked/unchecked via workflow JSON
  2. Radio buttons can be selected via workflow JSON
  3. Number and email inputs are typed correctly with validation
  4. Unit tests cover all new element types
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Add NUMBER/EMAIL to ElementType, SELECT_RADIO to ActionType, BasePage.select_radio method, Pydantic enum membership test
- [x] 02-02-PLAN.md — Wire SELECT_RADIO dispatch in ElementActions.execute(); add four dispatch unit tests (radio select, radio idempotency, number input, email input)

### Phase 3: Support Tab Switching and New Window Focus
**Goal**: Enable workflow JSON to switch browser tabs and focus on them in a new Chrome window
**Depends on**: Phase 2
**Success Criteria** (what must be TRUE):
  1. Workflow JSON can declare a tab-switch action that opens/switches to a new browser tab or window
  2. The framework focuses (brings to foreground) the newly opened Chrome window
  3. Subsequent page/section/element actions in the workflow execute in the new window context
  4. Unit tests cover tab-switch dispatch and window focus handling
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Add SWITCH_TO_NEW_WINDOW/TAB/LATEST_WINDOW to ActionType; add BasePage.open_new_window() and switch_to_latest_window(); write test_base_page_window.py (GREEN) and three RED dispatch stubs in test_action_dispatch.py
- [x] 03-02-PLAN.md — Wire three dispatch branches in ElementActions.execute(); create testdata/workflows/tabs/new_window_tab.json fixture; all tests go GREEN

### Phase 4: Support Dynamic Placeholder Expansion
**Goal**: Enable workflow JSON values to contain `${placeholder}` tokens that are resolved at action-dispatch time via a registry of generator functions
**Depends on**: Phase 3
**Success Criteria** (what must be TRUE):
  1. A `PLACEHOLDER_REGISTRY` maps token names to generator functions
  2. `resolve_dynamic_value()` detects `${placeholder}` patterns and calls the registered generator
  3. `JsonLoader` passes every element value through `resolve_dynamic_value()`
  4. `generate_sin_number()` returns a valid random Canadian SIN
  5. `generate_first_name()` and `generate_last_name()` return random names
  6. Unit tests cover resolution, passthrough (no placeholder), and unknown placeholder behavior
**Plans**: 1 plan

Plans:
- [x] 04-01-PLAN.md — Write test stubs RED (Wave 0), implement PLACEHOLDER_REGISTRY + generator functions + resolve_dynamic_value() in value_resolver.py, wire ValueResolver._resolve_string(), all tests GREEN

### Phase 5: Support wait_seconds in WaitConditionType
**Goal**: Add a `wait_seconds` condition to `WaitConditionType` so workflow JSON can declare a fixed-duration pause in `pre_wait` / `post_wait` without requiring a locator or element condition. The existing `WaitConditionDefinition.timeout` field is reused as the sleep duration (no schema change).
**Depends on**: Phase 4
**Success Criteria** (what must be TRUE):
  1. `WaitConditionType.WAIT_SECONDS` enum value exists
  2. `WaitConditionDefinition.timeout` is reused as the sleep duration for `wait_seconds` (no schema change — per D-01)
  3. `WaitManager._dispatch()` handles `WAIT_SECONDS` by calling a dedicated `_sleep_seconds()` helper
  4. Sleep helper is isolated on `WaitManager`, logged at WARNING, and commented with the reason (per CLAUDE.md §Synchronization layer)
  5. Unit tests cover the new condition type via pre_wait and post_wait
**Plans**: 1 plan

Plans:
- [x] 05-01-PLAN.md — TDD: RED tests for WaitConditionDefinition + WaitManager dispatch of WAIT_SECONDS; GREEN implementation adds enum value, `_sleep_seconds()` helper, and dispatch branch

### Phase 6: Support execute_js_script Action Type
**Goal**: Add an `EXECUTE_JS_SCRIPT` action type so workflow JSON can execute arbitrary JavaScript in the browser via the `value` field of an `ElementDefinition`. No locator is required when used as a standalone script action.
**Depends on**: Phase 5
**Success Criteria** (what must be TRUE):
  1. `ActionType.EXECUTE_JS_SCRIPT` enum value exists
  2. `ElementActions.execute()` dispatches `EXECUTE_JS_SCRIPT` by calling `driver.execute_script(element.value)`
  3. The `value` field carries the JavaScript string to execute
  4. Unit tests cover successful dispatch and verify `execute_script` is called with the correct JS
**Plans**: 1 plan

Plans:
- [x] 06-01-PLAN.md — TDD: RED tests for SCRIPT/EXECUTE_JS_SCRIPT enum membership and execute_script dispatch; GREEN implementation adds two enum values and elif branch in ElementActions.execute()

### Phase 7: Support skip-if-not-visible
**Goal**: Add conditional execution to element actions: when `options.skip_if_not_visible` is `true`, the engine checks element visibility at dispatch time. If not visible, the step is recorded as `SKIPPED` (not `FAILED`) and execution continues to the next element.
**Depends on**: Phase 6
**Success Criteria** (what must be TRUE):
  1. `SkipElementSignal` exception class exists in `src/core/exceptions.py`
  2. `ActionFactory.run()` raises `SkipElementSignal` before pre_wait when `skip_if_not_visible=True` and element is not visible
  3. `WorkflowEngine._run_element()` catches `SkipElementSignal` and calls `record_skip()` (not `record_fail()`)
  4. Visibility probe runs before pre_wait — no wait cost for skipped elements
  5. Unit tests cover: signal raised, no signal when visible, pre_wait skipped, skipped count increments
**Plans**: 1 plan

Plans:
- [x] 07-01-PLAN.md — TDD: RED tests for SkipElementSignal raise and engine catch; GREEN implementation adds exception, factory guard using BasePage.is_visible(), and _run_element() except branch

### Phase 8: Support checkbox search by name+value
**Goal**: Enable CHECK and UNCHECK actions to locate a specific checkbox by its HTML `value` attribute when multiple `<input type="checkbox">` elements share the same `name` attribute. When `locator.by == "name"` and `element.value` is non-empty, the framework builds a targeted CSS selector. Mirrors select_radio pattern exactly.
**Depends on**: Phase 7
**Success Criteria** (what must be TRUE):
  1. `BasePage.check()` and `BasePage.uncheck()` accept optional `value: str = ""` param
  2. When `value` is non-empty and `locator.by == "name"`, CSS selector `input[type="checkbox"][name="..."][value="..."]` is built and used
  3. When `value` is empty or `locator.by != "name"`, plain locator is used (backwards compatible)
  4. `ElementActions.execute()` CHECK and UNCHECK branches pass resolved value through to the updated methods
  5. Unit tests cover: value-present path, value-absent path, already-checked idempotency, already-unchecked idempotency
**Plans**: 1 plan

Plans:
- [x] 08-01-PLAN.md — TDD: RED tests for value passthrough dispatch and CSS selector construction; GREEN implementation extends check/uncheck signatures and updates CHECK/UNCHECK dispatch branches

### Phase 9: Support last-day-of-month placeholder
**Goal**: Add a `${last_day_of_month}` placeholder to `PLACEHOLDER_REGISTRY` in `value_resolver.py` that returns the last calendar date of the current month formatted as `MM/DD/YYYY`. No schema changes — pure registry extension following the Phase 4 pattern.
**Depends on**: Phase 4
**Success Criteria** (what must be TRUE):
  1. `generate_last_day_of_month()` returns a valid `MM/DD/YYYY` string for the last day of the current month
  2. `PLACEHOLDER_REGISTRY["last_day_of_month"]` maps to the generator
  3. `${last_day_of_month}` in workflow JSON `value` resolves at action-dispatch time
  4. Handles all months correctly including leap-year February
  5. Unit tests cover: correct format, correct last-day value, passthrough unchanged for non-placeholder values
**Plans**: 1 plan

Plans:
- [x] 09-01-PLAN.md — TDD: RED tests for generate_last_day_of_month import and TestLastDayOfMonth class; GREEN implementation adds calendar import, generator function, and PLACEHOLDER_REGISTRY entry

### Phase 10: Support ${env:KEY} config placeholder
**Goal**: Add an `${env:KEY}` placeholder namespace to `PLACEHOLDER_REGISTRY` in `value_resolver.py` so workflow JSON can reference values from the env YAML config (and `.env`) rather than hardcoding them — enabling account numbers, credentials, and environment-specific IDs to live in config files.
**Depends on**: Phase 4
**Success Criteria** (what must be TRUE):
  1. `${env:KEY}` in a workflow JSON `value` field resolves to the matching key from the active env YAML config
  2. Missing keys raise a clear error at resolution time (not silently pass through)
  3. Works alongside existing placeholders — `${sin_number}`, `${env:BASE_URL}`, etc. can all appear in the same workflow
  4. Unit tests cover: successful resolution, missing key error, passthrough of non-placeholder strings
**Plans**: 1 plan

Plans:
- [x] 10-01-PLAN.md — TDD: RED tests for configure_env_resolver import and TestEnvPlaceholder class; GREEN implementation adds _ENV_CONFIG singleton, configure_env_resolver(), env: branch in resolve_dynamic_value(), and AppConfig wiring

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Support Nested JSON | 2/2 | Complete | 2026-05-15 |
| 2. Support More Web Elements | 2/2 | Complete | 2026-05-16 |
| 3. Support Tab Switching and New Window Focus | 2/2 | Complete | 2026-05-15 |
| 4. Support Dynamic Placeholder Expansion | 1/1 | Complete | 2026-05-25 |
| 5. Support wait_seconds in WaitConditionType | 1/1 | Complete | 2026-05-26 |
| 6. Support execute_js_script Action Type | 1/1 | Complete | 2026-05-25 |
| 7. Support skip-if-not-visible | 1/1 | Complete | 2026-05-26 |
| 8. Support checkbox search by name+value | 1/1 | Complete | 2026-05-26 |
| 9. Support last-day-of-month placeholder | 1/1 | Complete | 2026-05-29 |
| 10. Support ${env:KEY} config placeholder | 1/1 | Complete   | 2026-05-30 |
