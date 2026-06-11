---
phase: 22-support-updating-a-group-of-similar-web-elements-together-sa
verified: 2026-06-11T15:18:39Z
status: passed
score: 11/11
overrides_applied: 0
---

# Phase 22: index_range Loop Expansion — Verification Report

**Phase Goal:** One ElementDefinition carrying an `${index}` token plus a new inclusive `index_range:[start,end]` field expands into N per-index interactions — each sharing the same type/action/value, with `${index}` substituted (embedded anywhere) into the element name and `locator.value`, recorded as one StepResult per index. A failed index continues the group; a missing index honors `skip_if_not_visible`. `index` is a reserved param name. Reuses the Phase 17 anchored-value and Phase 21 partial-locator expansion paths unchanged.

**Verified:** 2026-06-11T15:18:39Z
**Status:** PASSED
**Re-verification:** No — initial verification
**Test result:** `python -m pytest tests/unit/ -q` → **435 passed, 0 failed**

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | D-01: `index_range` field accepted on `ElementDefinition`, `None` by default; existing JSON unaffected | VERIFIED | `workflow_models.py:92` — `index_range: Optional[List[int]] = None`; `TestIndexRange::test_no_index_range_defaults_to_none` passes |
| 2 | D-02: `index_range:[start,end]` is inclusive both ends; length!=2 or start>end raises ValidationError at load | VERIFIED | `validate_index_range` validator at `workflow_models.py:106-121`; `test_range_0_to_3_produces_four_calls` (4 calls for [0,3]), `test_start_greater_than_end_raises`, `test_length_not_2_raises` all pass |
| 3 | D-03: `${index}` substitutes embedded anywhere in `locator.value` (id and XPath) via the existing Phase 21 params path | VERIFIED | Engine substitutes via `.replace` at `workflow_engine.py:145-148`; `test_embedded_index_in_locator_value` (asserts `captured_elements[2].locator.value == "el_2"`) and `test_xpath_locator_with_index` (asserts all 3 XPath values resolved) pass |
| 4 | D-04: `${index}` substitutes in element name so each StepResult shows the concrete per-index name | VERIFIED | `workflow_engine.py:143` — `concrete_name = element.name.replace("${index}", str(i))`; `test_step_result_shows_concrete_name` asserts `steps[2].element_name == "amount_2"` |
| 5 | D-05: The same value is applied to every index | VERIFIED | `workflow_engine.py:149-155` — `concrete_elem = element.model_copy(update=update)` carries original `value`; `test_same_value_all_indices` asserts all 4 captured elements have `value == "100"` |
| 6 | D-06: `value` field stays `Optional[Any]` — a future per-index value list is an additive, non-breaking change (documented, not implemented) | VERIFIED | `workflow_models.py:80` — `value: Optional[Any] = None`; comment at lines 89-91 documents D-06; no per-index value list implemented |
| 7 | D-07: One StepResult is recorded per index | VERIFIED | `test_n_results_for_n_indices` asserts `len(summary().steps) == 4` for range [0,3] |
| 8 | D-08: A failed index does not stop remaining indices in the group | VERIFIED | `test_failed_index_does_not_stop_group` uses `side_effect=[None, ElementActionError("x"), None, None]`, asserts 4 steps, exactly 1 FAILED, 3 PASSED |
| 9 | D-09: A missing index honors `skip_if_not_visible` (SKIPPED when opted in, otherwise FAILED and group continues) | VERIFIED | `test_missing_index_skipped_when_skip_flag` asserts `statuses[1] == StepStatus.SKIPPED`; `test_missing_index_failed_without_skip_flag` asserts `statuses[1] == StepStatus.FAILED` with remaining indices still passing |
| 10 | reserved: A workflow param named `index` raises `WorkflowValidationError` at load (both `load` and `load_raw`) | VERIFIED | `json_loader.py:19` — `_RESERVED_PARAM_NAMES = frozenset({"index"})`; guards at lines 136-142 and 196-202; `test_index_param_raises` and `test_index_param_raises_in_load_raw` both pass |
| 11 | no-regression: Non-indexed elements and `value_resolver`/`locator_resolver` behavior are unchanged | VERIFIED | `test_non_indexed_element_unchanged` asserts single call/result for `index_range=None` element; `value_resolver.py` and `locator_resolver.py` not modified in any Phase 22 commit; `test_action_dispatch.py` (34 tests) all pass |

**Score:** 11/11 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/models/workflow_models.py` | `index_range` field + `validate_index_range` model_validator on `ElementDefinition` | VERIFIED | Field at line 92, validator at lines 106-121; messages contain `"2-element"` and `"<= end"` matching test `match=` regexes |
| `src/data/json_loader.py` | `_RESERVED_PARAM_NAMES` frozenset + reserved-name guard in both `load` and `load_raw` | VERIFIED | `_RESERVED_PARAM_NAMES` at line 19; guards at lines 136-142 and 196-202; both raise `WorkflowValidationError` with message containing `"reserved"` |
| `src/workflow/workflow_engine.py` | `_run_section` loop expansion + `_run_element` `params_override` kwarg | VERIFIED | Loop expansion at lines 119-156; `params_override: dict | None = None` at line 163; params selection at line 171 |
| `tests/unit/test_index_expansion.py` | `TestIndexExpansion` with 10 engine-level methods (D-02a, D-03, D-03b, D-04, D-05, D-07, D-08, D-09, D-09b, no-regression) | VERIFIED | 295-line file; all 10 methods confirmed; uses real `ResultCollector`, mocked driver/WaitManager, patched `ActionFactory.run`; no `time.sleep`, no real browser |
| `tests/unit/test_workflow_models.py` | `TestIndexRange` class with 5 methods | VERIFIED | Class at line 335; methods: `test_no_index_range_defaults_to_none`, `test_valid_index_range_accepted`, `test_single_element_range_accepted`, `test_start_greater_than_end_raises`, `test_length_not_2_raises` |
| `tests/unit/test_json_loader.py` | `TestReservedParamName` class with 3 methods | VERIFIED | Class at line 242; methods: `test_index_param_raises`, `test_index_param_raises_in_load_raw`, `test_non_reserved_param_accepted` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_run_section` | `_run_element` | `params_override=merged_params` with `model_copy`'d concrete name | WIRED | `workflow_engine.py:153-156` — `self._run_element(concrete_elem, ..., params_override=merged_params)` |
| `_run_element` | `ActionFactory` | `ActionFactory(section, self._wm, params=params)` where `params = params_override or self._params` | WIRED | `workflow_engine.py:171-172` — selection and construction confirmed |
| `json_loader.py` | `WorkflowValidationError` | `raise` on reserved `index` param in both params-loops | WIRED | `json_loader.py:136-142` (load) and `196-202` (load_raw) both raise with `path=str_path` and message containing `"reserved"` |

---

## Data-Flow Trace (Level 4)

Not applicable — Phase 22 delivers logic/engine code, not components rendering dynamic data to a UI. The test suite directly asserts data flow: `merged_params` carries `{"index": str(i)}` per iteration (verified by `test_embedded_index_in_locator_value` asserting the concrete element received by `ActionFactory.run` already has the resolved locator value).

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 22 tests (all 18) | `python -m pytest tests/unit/test_index_expansion.py::TestIndexExpansion tests/unit/test_workflow_models.py::TestIndexRange tests/unit/test_json_loader.py::TestReservedParamName -v` | 18 passed | PASS |
| Full unit suite (no regression) | `python -m pytest tests/unit/ -q` | 435 passed, 0 failed | PASS |
| Action dispatch backward-compat | Part of 435 above — `test_action_dispatch.py` (34 tests) included | 34 passed | PASS |

---

## Probe Execution

No probes declared in PLAN or conventionally expected. Step 7c: SKIPPED (no phase-specific probe scripts).

---

## Requirements Coverage

Requirements for this phase are defined in `22-CONTEXT.md` decisions D-01..D-09 (no formal REQUIREMENTS.md for this project). The PLAN 02 `requirements` field lists: D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, reserved, no-regression.

| Requirement | Plan | Description | Status | Evidence |
|-------------|------|-------------|--------|----------|
| D-01 | 22-02 | `index_range` field defaults to None; legacy JSON unaffected | SATISFIED | `workflow_models.py:92`; `test_no_index_range_defaults_to_none` green |
| D-02 | 22-02 | `[start,end]` inclusive; length!=2 or start>end raises ValidationError | SATISFIED | `validate_index_range` validator; 3 failing-path tests green |
| D-03 | 22-02 | `${index}` substituted embedded anywhere in `locator.value` | SATISFIED | Engine `.replace` at lines 145-148; test asserts `captured_elements[2].locator.value == "el_2"` |
| D-04 | 22-02 | `${index}` in element name → concrete per-index StepResult name | SATISFIED | `concrete_name` at line 143; `test_step_result_shows_concrete_name` green |
| D-05 | 22-02 | Same value applied to all indices | SATISFIED | `model_copy` carries original `value`; `test_same_value_all_indices` green |
| D-06 | 22-02 | `value` stays `Optional[Any]`; future per-index list is additive | SATISFIED | `workflow_models.py:80`; documented in comment at lines 89-91 |
| D-07 | 22-02 | One StepResult per index | SATISFIED | `test_n_results_for_n_indices` green |
| D-08 | 22-02 | Failed index does not stop group | SATISFIED | `test_failed_index_does_not_stop_group` green |
| D-09 | 22-02 | Missing index honors `skip_if_not_visible` | SATISFIED | Both skip and non-skip tests green |
| reserved | 22-02 | Workflow param named `index` raises `WorkflowValidationError` at load (load + load_raw) | SATISFIED | `_RESERVED_PARAM_NAMES` in both loader entry points; 2 load-path tests green |
| no-regression | 22-02 | Non-indexed elements and value/locator resolver behavior unchanged | SATISFIED | `value_resolver.py` / `locator_resolver.py` untouched per commit history; `test_non_indexed_element_unchanged` and full `test_action_dispatch.py` green |

---

## Anti-Patterns Found

Scanned all 6 phase-modified files for TBD / FIXME / XXX / TODO / HACK / PLACEHOLDER / `time.sleep`.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | — |

No debt markers found. No `time.sleep` calls. No placeholder or stub code.

---

## Code Review Advisory — CR-01 Scope Assessment

The code review (22-REVIEW.md) flagged CR-01 as "BLOCKER": the reserved-`index` guard exists only in `WorkflowLoader.load` / `load_raw`, not at the `WorkflowDefinition` / `ParameterDefinition` model level. A `WorkflowDefinition` built in-process without the loader can carry an `index` parameter that `self._params` will then contain, and the per-iteration merge `{**self._params, "index": str(i)}` silently overwrites it.

**Assessment against the phase goal:**

The phase goal states `index is a reserved param name`. The PLAN 02 must_have scopes this as: `"reserved: a workflow param named index raises WorkflowValidationError at load (both load and load_raw)"`. The threat model T-22-03 disposes the threat as "mitigate" via `json_loader` guard. The phase delivered exactly what it promised: both loader entry points enforce the guard and the corresponding tests pass.

CR-01 identifies a real defense-in-depth gap but it is advisory relative to the phase contract: the phase goal did not commit to model-level enforcement, and the loader-level guard covers the primary attack surface (JSON file input). The CR-01 finding is correctly routed to `/gsd-code-review --fix` for a follow-up phase or fix.

**This does not block the phase goal.** The reserved-name truth is VERIFIED per the stated scope.

---

## Human Verification Required

One optional smoke test is noted in 22-VALIDATION.md under "Manual-Only Verifications":

**Test:** Author a sample workflow JSON with `index_range: [0,3]` and run a smoke test against a fixture page with indexed inputs (`amount_0..amount_3`).
**Expected:** One result row per index; each filled with the specified value.
**Why human:** Requires a live AJAX page with the indexed elements.

The VALIDATION.md explicitly marks this as "optional confirmation, not a phase gate." It is informational only and does not affect the phase status.

---

## Gaps Summary

No gaps. All 11 must-have truths verified, all artifacts substantive and wired, all 435 unit tests passing, no debt markers.

The one code review advisory (CR-01: model-level reserved-name enforcement) is a known defense-in-depth improvement routed to the user for follow-up — it does not contradict the phase goal, which scoped enforcement to load time.

---

_Verified: 2026-06-11T15:18:39Z_
_Verifier: Claude (gsd-verifier)_
