# Roadmap: UI Workflow Automation

## Overview

Data-driven Selenium automation framework that reads workflow definitions from JSON and executes browser interactions across a hierarchy of Workflow → Tabs → Pages → Sections → Elements. Phases extend the framework's capabilities incrementally.

## Phases

- [x] **Phase 1: Support Nested JSON** - `$ref` file-reference resolution in workflow loader
- [x] **Phase 2: Support More Web Elements** - checkBox, radio, number, email element actions

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

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Support Nested JSON | 2/2 | Complete | 2026-05-15 |
| 2. Support More Web Elements | 2/2 | Complete | 2026-05-16 |
