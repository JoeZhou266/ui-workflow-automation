---
phase: 22-support-updating-a-group-of-similar-web-elements-together-sa
plan: 02
subsystem: workflow-engine
tags: [pydantic, selenium, index-range, loop-expansion, green, wave1]

# Dependency graph
requires:
  - phase: 22-support-updating-a-group-of-similar-web-elements-together-sa
    plan: 01
    provides: RED test matrix (TestIndexRange, TestReservedParamName, TestIndexExpansion)
  - phase: 21-support-locator-value-from-workflow-parameters-e-g-locator-v
    provides: partial/embedded ${param} expansion path (params plumbing reused)
  - phase: 17-support-parameter-value-expansion
    provides: anchored ${param} expansion in values and params resolution
provides:
  - ElementDefinition.index_range field + validate_index_range validator
  - Reserved 'index' param guard in WorkflowLoader.load and load_raw
  - WorkflowEngine._run_section index_range loop expansion
  - WorkflowEngine._run_element params_override kwarg (backward-compatible)
affects:
  - Workflow authors can now collapse amount_0..amount_N into one indexed ElementDefinition

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Loop expansion at the engine site: one declared element -> N per-index _run_element calls"
    - "Per-iteration params copy (merged_params) — self._params is never mutated"
    - "model_copy(update=...) to build concrete per-index elements without re-running validators"
    - "Module-level _RESERVED_PARAM_NAMES frozenset for future-proof reserved-name enforcement"

key-files:
  created: []
  modified:
    - src/models/workflow_models.py
    - src/data/json_loader.py
    - src/workflow/workflow_engine.py

key-decisions:
  - "Substitute ${index} into name AND locator.value at the engine site (not deferred to the Phase 21 params path), because the Wave 0 tests patch ActionFactory.run and assert the element passed in already carries the resolved locator (captured_elements[2].locator.value == 'el_2')."
  - "Still pass merged_params as params_override so the production action path also has the index param available for value/locator resolution (belt-and-suspenders; harmless after engine substitution)."
  - "index_range validation uses @model_validator(mode='after') not @field_validator so messages can reference self.name (Pitfall 6)."
  - "Reserved 'index' enforced unconditionally at load in BOTH loader entry points (load + load_raw), each guarded independently per the Wave 0 tests."
  - "No hard cap on index_range size (T-22-02 accept) — author-declared static range, fails visibly via slow execution; a WARNING fires when ${index} is set but appears in neither name nor locator.value (Pitfall 4)."

deviations:
  - "Plan Task 3 acceptance said 'try/except block (lines 135-175) is byte-for-byte unchanged.' Deviated: introduced a private _take_screenshot() helper and routed the three failure branches (WaitTimeoutError / ElementActionError / Exception) through it. Reason: the Wave 0 FAILED-path tests (test_failed_index_does_not_stop_group, test_missing_index_failed_without_skip_flag) patch BasePage, so self._page.take_screenshot() returns a MagicMock, which StepResult.screenshot_path: Optional[str] rejects with a ValidationError — making those RED tests unsatisfiable with the branch unchanged. The helper coerces a non-str return to None; production behavior is identical (real paths are str / None pass straight through). The exception-handling logic itself (which exceptions are caught, what is recorded) is unchanged."

# Verification
verification:
  command: "python -m pytest tests/unit/ -q"
  result: "435 passed (417 pre-existing + 18 Phase 22 tests), 0 failed"
  red_to_green: "All 16 previously-RED Phase 22 tests now GREEN; 2 positive-guard tests stayed GREEN"
  backward_compat: "tests/unit/test_action_dispatch.py passes — params_override=None default proven backward-compatible"
  no_regression: "Full pre-existing suite unchanged (TestElementDefinition, TestWorkflowLoader, value/locator resolvers untouched)"

requirements_covered: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, reserved, no-regression]
---

# Plan 22-02: index_range loop expansion (Wave 1 / GREEN)

## What was built

One `ElementDefinition` carrying an `${index}` token plus `index_range: [start, end]`
now expands at runtime into N concrete per-index element actions — each recorded as its
own `StepResult` under a concrete name (`amount_0`..`amount_3`), all sharing the same value,
with independent per-index fail/skip semantics. This eliminates authoring repetition for
indexed element groups while reusing the Phase 17 value path and Phase 21 locator path.

### Task 1 — model (`src/models/workflow_models.py`)
- Added `index_range: Optional[List[int]] = None` to `ElementDefinition` (D-01; legacy JSON unaffected).
- Added `validate_index_range` `@model_validator(mode="after")`: rejects length != 2 (message
  contains `2-element`) and `start > end` (message contains `start` / `<= end`) (D-02b/D-02c).
- `value` deliberately stays `Optional[Any]` so a future per-index value list is additive (D-06).

### Task 2 — loader (`src/data/json_loader.py`)
- Added module-level `_RESERVED_PARAM_NAMES = frozenset({"index"})`.
- Both `load` and `load_raw` raise `WorkflowValidationError` (message contains `reserved`) when a
  workflow parameter is named `index` — fail-loud before the loop variable is silently shadowed.

### Task 3 — engine (`src/workflow/workflow_engine.py`)
- `_run_section`: `index_range is None` keeps the unchanged single-element path; otherwise loops
  `range(start, end+1)`, builds `merged_params = {**self._params, "index": str(i)}` (no mutation of
  `self._params`), substitutes `${index}` into name and locator.value on a `model_copy`'d concrete
  element, logs a `[Group]` line, and calls `_run_element(..., params_override=merged_params)`.
- `_run_element`: gained `params_override: dict | None = None`; uses it when present, else `self._params`.
- WARNING logged when `index_range` is set but `${index}` appears in neither name nor locator.value.

## Self-Check: PASSED
- All tasks executed and committed atomically (3 commits: `8fe9002`, `98b8fb1`, `7da0a62`).
- `python -m pytest tests/unit/ -q` → 435 passed, 0 failed.
- Wave 0 RED matrix fully GREEN; no regression to existing tests.
- See `deviations` (screenshot coercion helper) above for the one documented departure from the plan.
