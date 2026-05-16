---
phase: 03-support-tab-switching-new-window
fixed_at: 2026-05-15T00:00:00Z
review_path: .planning/phases/03-support-tab-switching-new-window/03-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-05-15
**Source review:** .planning/phases/03-support-tab-switching-new-window/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `switch_to_latest_window` — unguarded `.pop()` on empty set crashes with `KeyError`

**Files modified:** `src/ui/base_page.py`
**Commit:** 3c59a0a
**Applied fix:** Added an explicit `if not new_handles:` guard before `new_handles.pop()` in `switch_to_latest_window`. When the set difference is empty, raises `ElementActionError("No new window handle found after waiting", element_name="switch_to_latest_window")` instead of allowing a `KeyError` to propagate with a meaningless traceback.

---

### WR-02: `SWITCH_TO_NEW_WINDOW` / `SWITCH_TO_NEW_TAB` ignore the element locator — action semantics are ambiguous

**Files modified:** `src/actions/element_actions.py`
**Commit:** 281575b
**Applied fix:** Added inline comments to both `ActionType.SWITCH_TO_NEW_WINDOW` and `ActionType.SWITCH_TO_NEW_TAB` dispatch branches explicitly stating that `element.locator` is not used because these actions open a blank window/tab programmatically. This resolves the ambiguity without changing runtime behaviour, matching the reviewer's Option A recommendation.

---

### WR-03: `test_workflow_models.py` uses Pydantic v2 `model_validate()` without version guard

**Files modified:** `tests/unit/test_workflow_models.py`
**Commit:** 9d72b35
**Applied fix:** Added `import pydantic`, a module-level `_PYDANTIC_V2` boolean flag, and a `requires_pydantic_v2` mark (`pytest.mark.skipif`). Applied `@requires_pydantic_v2` to all five test methods inside `TestWorkflowDefinition` that call `WorkflowDefinition.model_validate(...)`. Confirmed installed version is Pydantic 2.13.3, so all tests continue to run on the current environment; the guard protects against v1 environments.

---

_Fixed: 2026-05-15_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
