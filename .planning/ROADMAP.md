# Roadmap: UI Workflow Automation

## Overview

Data-driven Selenium automation framework that reads workflow definitions from JSON and executes browser interactions across a hierarchy of Workflow → Tabs → Pages → Sections → Elements. Phases extend the framework's capabilities incrementally.

## Phases

- [x] **Phase 1: Support Nested JSON** - `$ref` file-reference resolution in workflow loader
- [x] **Phase 2: Support More Web Elements** - checkBox, radio, number, email element actions
- [x] **Phase 3: Support Tab Switching and New Window Focus** - switch tab / new window via workflow JSON
- [ ] **Phase 4: Support Dynamic Placeholder Expansion** - registry-based ${placeholder} expansion in workflow JSON values

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
- [ ] 04-01-PLAN.md — Write test stubs RED (Wave 0), implement PLACEHOLDER_REGISTRY + generator functions + resolve_dynamic_value() in value_resolver.py, wire ValueResolver._resolve_string(), all tests GREEN

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Support Nested JSON | 2/2 | Complete | 2026-05-15 |
| 2. Support More Web Elements | 2/2 | Complete | 2026-05-16 |
| 3. Support Tab Switching and New Window Focus | 2/2 | Complete | 2026-05-15 |
| 4. Support Dynamic Placeholder Expansion | 0/1 | Not started | — |
