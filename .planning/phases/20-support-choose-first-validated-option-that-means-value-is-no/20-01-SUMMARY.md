---
phase: 20-support-choose-first-validated-option-that-means-value-is-no
plan: "01"
subsystem: ui/base_page
tags: [tdd, select, sentinel, first_valid, unit-test]
dependency_graph:
  requires: []
  provides: [first_valid-sentinel]
  affects: [src/ui/base_page.py]
tech_stack:
  added: []
  patterns: [sentinel-branch, private-helper, mock-Select]
key_files:
  created:
    - tests/unit/test_base_page_select_first_valid.py
  modified:
    - src/ui/base_page.py
decisions:
  - "sentinel check (value.strip().lower() == 'first_valid') precedes int(value) cast to prevent ValueError"
  - "opt.click() used (not Select._set_selected) so change/input events fire for AJAX-heavy pages"
  - "opt.get_attribute('value') with None-guard before .strip() handles absent value attributes"
  - "ElementActionError raised when no qualifying option found — step records FAILED, no silent skip"
metrics:
  duration: "~5 minutes"
  completed: "2026-06-07"
  tasks_completed: 2
  files_changed: 2
---

# Phase 20 Plan 01: first_valid Sentinel for select_by_index Summary

**One-liner:** Added `first_valid` sentinel path to `select_dropdown` that selects the first `<option>` with a non-empty `value` attribute via a new `_select_first_valid_option` private helper, with full TDD RED/GREEN coverage.

## What Was Built

A confined, purely additive change to `src/ui/base_page.py`:

1. **Sentinel branch in `select_dropdown`** — before the existing `int(value)` cast, added `value.strip().lower() == "first_valid"` check that routes to `_select_first_valid_option(sel, name)`. The numeric path is byte-for-byte unchanged.

2. **`_select_first_valid_option` helper** — iterates `sel.options` (DOM order), reads `opt.get_attribute("value")`, skips `None`/empty/whitespace-only values, clicks the first qualifying option, raises `ElementActionError` if none qualify.

3. **8 unit tests** (`TestSelectFirstValid`) covering FV-01..FV-06, FV-08, FV-09.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Write failing unit tests | be05cd4 | tests/unit/test_base_page_select_first_valid.py |
| 2 (GREEN) | Implement sentinel branch + helper | 85bc864 | src/ui/base_page.py |

## TDD Gate Compliance

- RED gate: `test(20-01)` commit `be05cd4` — 8 tests collected, all failing (ValueError on int("first_valid"))
- GREEN gate: `feat(20-01)` commit `85bc864` — all 8 tests pass, 402 total unit tests green

## Verification Results

- `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py -v` — 8/8 passed (FV-01..FV-06, FV-08, FV-09)
- `.venv/bin/pytest tests/unit/test_action_dispatch.py::TestElementActions::test_select_by_index -x` — 1/1 passed (FV-07 regression)
- `.venv/bin/pytest tests/unit/ -v` — 402 passed, 0 regressions

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — all option-scan logic is fully implemented; no placeholder data or hardcoded returns.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Change confined to read-only DOM interaction via Selenium.

## Self-Check: PASSED

- [x] `tests/unit/test_base_page_select_first_valid.py` exists
- [x] `src/ui/base_page.py` contains `_select_first_valid_option` (2 occurrences: definition + call site)
- [x] Commit `be05cd4` exists (RED)
- [x] Commit `85bc864` exists (GREEN)
- [x] 402 unit tests pass, 0 regressions
- [x] `src/actions/element_actions.py` unmodified
