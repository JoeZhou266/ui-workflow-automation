---
phase: 22-support-updating-a-group-of-similar-web-elements-together-sa
fixed_at: 2026-06-11T00:00:00Z
review_path: .planning/phases/22-support-updating-a-group-of-similar-web-elements-together-sa/22-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 22: Code Review Fix Report

**Fixed at:** 2026-06-11
**Source review:** .planning/phases/22-support-updating-a-group-of-similar-web-elements-together-sa/22-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (1 Critical + 6 Warning; Info findings out of scope)
- Fixed: 7
- Skipped: 0
- Unit suite: 435 passed (baseline) → 445 passed (10 new tests added, 0 regressions)

The TDD-contract tests (`TestIndexRange`, `TestReservedParamName`, `tests/unit/test_index_expansion.py`)
remained green throughout and were not modified to make any fix pass.

## Fixed Issues

### CR-01: Reserved-name guard for `index` is bypassed by `WorkflowEngine.__init__`

**Files modified:** `src/core/constants.py`, `src/models/workflow_models.py`, `tests/unit/test_workflow_models.py`
**Commit:** e5b68d9
**Status:** fixed: requires human verification (security/correctness invariant — confirm the model-boundary guard is the intended enforcement layer)
**Applied fix:** Added `RESERVED_PARAM_NAMES` (and `INDEX_PARAM_NAME`) to `src/core/constants.py`
and a `@model_validator(mode="after") reject_reserved_param_names` on `WorkflowDefinition`.
The reserved-name invariant now holds for every construction path — `model_validate` (loader),
direct `WorkflowDefinition(...)` construction, and the engine constructor alike — so a param named
`index` can no longer be silently shadowed by the loop counter in `_run_section`. The loader's
existing string-level check in `_RESERVED_PARAM_NAMES` is intentionally kept as an earlier/clearer
error for JSON input; the existing `TestReservedParamName` loader tests still pass. Added a new
`TestReservedParamNameModelBoundary` class covering `model_validate`, direct construction, and the
non-reserved accept path.

### WR-01: `index_range` allows negative `start`, producing malformed locators

**Files modified:** `src/models/workflow_models.py`, `tests/unit/test_workflow_models.py`
**Commit:** 2844b23
**Status:** fixed
**Applied fix:** Added a `start < 0` check to `validate_index_range` raising a clear
`"must be >= 0"` error. Added `test_negative_start_raises` and `test_zero_start_accepted`
(boundary) to `TestIndexRange`.

### WR-02: No upper bound on `index_range` span (unbounded expansion)

**Files modified:** `src/core/constants.py`, `src/models/workflow_models.py`, `tests/unit/test_workflow_models.py`
**Commit:** 9d3188e
**Status:** fixed
**Applied fix:** Added a module constant `MAX_INDEX_SPAN = 1000` to `src/core/constants.py`
and a span check (`end - start + 1 > MAX_INDEX_SPAN`) to `validate_index_range`, mirroring the
existing bounds on `retry_count` (<=10) and `timeout` (<=300). A typo like `[0, 1000000]` now fails
loud at load time. Added `test_span_at_max_accepted` (boundary) and `test_span_over_max_raises`.

### WR-03: `${index}` is silently NOT resolved inside `element.value`

**Files modified:** `src/workflow/workflow_engine.py`, `tests/unit/test_index_expansion.py`
**Commit:** 26c3be5
**Status:** fixed: requires human verification (logic/behavior change — confirm engine-site value
substitution is the desired rule over the documented-limitation alternative)
**Applied fix:** Chose option (b) from the review — substitute `${index}` inside `element.value`
at the engine site (substring `.replace`) when the value is a string containing the token, so it
resolves consistently with `name` and `locator.value`. An embedded value like `"row_${index}_amount"`
now expands per index instead of being typed verbatim. A full-token `"${index}"` continues to resolve
(now via the engine-site substring replace, with the downstream `merged_params` path as backstop).
Added `test_embedded_index_in_value` and `test_full_token_value_still_resolves`.

### WR-04: Duplicate `${index}`-substitution logic diverges from name handling

**Files modified:** `src/workflow/workflow_engine.py`
**Commit:** 9b99874
**Status:** fixed: requires human verification (engine loop refactor — confirm behavior parity)
**Applied fix:** Extracted a single static helper `_substitute_index(element, i)` that substitutes
`${index}` uniformly across `name`, `locator.value`, and `value` so the three cannot drift on future
edits. `_run_section` now calls it instead of inlining three different mechanisms. Switched the magic
strings `"${index}"` / `"index"` to the `INDEX_TOKEN` / `INDEX_PARAM_NAME` constants and added a comment
documenting that `INDEX_PARAM_NAME` intentionally remains in `merged_params` as a downstream backstop
(safe because the reserved-name guard prevents author collision). This is a behavior-preserving refactor
(same substring-replace semantics); flagged for human verification because it restructures the expansion
loop. Incidentally documents the IN-01 assumption (substitution only injects a stringified int, so the
un-revalidated `model_copy` stays valid).

### WR-05: `load` and `load_raw` duplicate the parameter-parsing + reserved-name block

**Files modified:** `src/data/json_loader.py`
**Commit:** b125025
**Status:** fixed
**Applied fix:** Extracted a single `WorkflowLoader._extract_params(data, str_path) -> dict` static
helper containing the shape check, reserved-name guard, and `resolve_dynamic_value` loop. Both `load`
and `load_raw` now call it, eliminating the copy-paste drift. As a deliberate convergence, `load_raw`
now also produces the `"Error resolving workflow parameters: ..."` message on value-resolution failure
(previously only `load` did). All 20 loader tests pass.

### WR-06: "Warn but don't raise" path for missing `${index}` token is untested

**Files modified:** `tests/unit/test_index_expansion.py`
**Commit:** a6adee9
**Status:** fixed
**Applied fix:** Added `test_missing_token_warns_and_runs_n_identical` which sets `index_range` with a
token-free `name` and `locator.value`, asserts `ActionFactory.run` is called N times, asserts all N
`StepResult`s collide on the identical concrete name (locking the deliberately-tolerated behavior), and
asserts (via `caplog`) that the WARNING is emitted.

## Notes on Info findings (out of scope)

Info findings IN-01..IN-04 were not in the `critical_warning` fix scope and were not separately
committed. Two were incidentally addressed while fixing warnings: IN-01 (un-revalidated `model_copy`)
is now documented in the `_substitute_index` docstring (WR-04), and IN-04 (magic `"${index}"` /
`"index"` strings) is mitigated by the new `INDEX_TOKEN` / `INDEX_PARAM_NAME` constants used by the
engine (WR-04). IN-02 and IN-03 remain open for a future iteration.

---

_Fixed: 2026-06-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
