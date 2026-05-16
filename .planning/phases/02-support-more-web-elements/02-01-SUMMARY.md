---
phase: 02-support-more-web-elements
plan: "01"
subsystem: core-enums-and-ui-primitives
tags:
  - selenium
  - pydantic
  - enums
  - action-dispatch
dependency_graph:
  requires: []
  provides:
    - ElementType.NUMBER
    - ElementType.EMAIL
    - ActionType.SELECT_RADIO
    - BasePage.select_radio
  affects:
    - src/actions/element_actions.py
tech_stack:
  added: []
  patterns:
    - Append-only enum extension (no reordering of existing values)
    - check/uncheck mirror pattern for select_radio idempotency guard
    - TDD RED/GREEN cycle for BasePage interaction method
key_files:
  created:
    - tests/unit/test_base_page_select_radio.py
  modified:
    - src/core/enums.py
    - src/ui/base_page.py
    - tests/unit/test_workflow_models.py
decisions:
  - SELECT_RADIO placed after UNCHECK in ActionType to group state-toggle actions together
  - NUMBER/EMAIL placed after FILE in ElementType for append-only ordering
  - select_radio unit tests placed in a new dedicated file (test_base_page_select_radio.py) since no base_page test file existed
metrics:
  duration_minutes: 2
  completed_date: "2026-05-16"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 3
---

# Phase 2 Plan 01: Schema and Interaction Primitives Summary

**One-liner:** Extended ElementType/ActionType enums with NUMBER, EMAIL, SELECT_RADIO and added idempotent BasePage.select_radio() mirroring the check() pattern.

## What Was Built

Three surgical additions that establish the contracts Plan 02 (dispatch wiring) will consume:

1. **`src/core/enums.py`** — Three new enum values added:
   - `ElementType.NUMBER = "number"` (after FILE)
   - `ElementType.EMAIL = "email"` (after NUMBER)
   - `ActionType.SELECT_RADIO = "select_radio"` (after UNCHECK)

2. **`src/ui/base_page.py`** — New method `select_radio` added immediately after `uncheck`:
   ```python
   def select_radio(self, locator: LocatorDefinition, name: str = "") -> None:
       """Select a radio button if not already selected."""
       el = self.wait_for_visible(locator)
       if not el.is_selected():
           el.click()
   ```

3. **`tests/unit/test_workflow_models.py`** — New test `test_number_and_email_element_types_are_valid` inside `TestElementDefinition` verifying Pydantic accepts both new element types.

4. **`tests/unit/test_base_page_select_radio.py`** — New TDD test file (4 tests) for `BasePage.select_radio`:
   - Happy path: clicks when not selected
   - Idempotency: no click when already selected
   - Synchronization contract: `wait_for_visible` called before DOM interaction
   - Signature: `name` optional, return value is `None`

## Final Enum State

```python
class ElementType(str, Enum):
    ...
    FILE = "file"
    NUMBER = "number"   # NEW
    EMAIL = "email"     # NEW

class ActionType(str, Enum):
    ...
    UNCHECK = "uncheck"
    SELECT_RADIO = "select_radio"  # NEW
    UPLOAD = "upload"
```

## Plan 02 Readiness

Plan 02 can now:
- Reference `ActionType.SELECT_RADIO` in the dispatch table without further setup
- Call `page.select_radio(locator, name)` from `ElementActions` without further setup
- Declare `type: "number"` or `type: "email"` in workflow JSON without Pydantic rejection

## Pytest Result

```
126 passed in 0.18s
```
All 121 pre-existing unit tests pass plus 5 new tests (1 model test + 4 select_radio behavior tests).

## Deviations from Plan

**1. [Rule 2 - Missing artifact] Created dedicated test file for BasePage.select_radio**
- **Found during:** Task 2 (TDD RED phase)
- **Issue:** No `tests/unit/test_base_page.py` existed; the plan said "unit test for select_radio lives in Plan 02" but TDD requires a RED commit. Created `tests/unit/test_base_page_select_radio.py` as a standalone file.
- **Fix:** 4 behavior tests in new file; no existing files modified.
- **Files modified:** tests/unit/test_base_page_select_radio.py (created)
- **Commit:** 64867db (RED), 483e01f (GREEN)

**2. [TDD Sequencing Note] Task 3 test passed immediately (expected)**
- Task 1 added `ElementType.NUMBER`/`EMAIL` before Task 3 wrote the verification test. The test passed on first run because implementation already existed from Task 1. This is correct per the plan's sequential task ordering — not a test design flaw.

## Known Stubs

None. All three additions are complete implementations with no placeholder values or TODO markers.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. Enum additions are internal Python constants; Pydantic continues to reject unknown string values outside the declared set.

## TDD Gate Compliance

Task 2 (BasePage.select_radio):
- RED gate: commit `64867db` — `test(02-01): add failing tests for BasePage.select_radio`
- GREEN gate: commit `483e01f` — `feat(02-01): add BasePage.select_radio() mirroring check() pattern`
- REFACTOR: not needed (implementation is already minimal and clean)

## Self-Check

Files created/modified:
- src/core/enums.py — FOUND
- src/ui/base_page.py — FOUND
- tests/unit/test_workflow_models.py — FOUND
- tests/unit/test_base_page_select_radio.py — FOUND

Commits:
- 4adc2a5 feat(02-01): enum additions
- 64867db test(02-01): RED tests for select_radio
- 483e01f feat(02-01): select_radio implementation
- 604587e test(02-01): Pydantic enum membership test

## Self-Check: PASSED
