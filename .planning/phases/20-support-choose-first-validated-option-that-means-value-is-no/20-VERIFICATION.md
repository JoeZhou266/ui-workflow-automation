---
phase: 20-support-choose-first-validated-option-that-means-value-is-no
verified: 2026-06-07T14:37:00Z
status: human_needed
score: 7/7 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run a smoke workflow JSON with {type: select, action: select_by_index, value: 'first_valid'} against a real browser page that has a <select> with a leading placeholder option (value='')"
    expected: "The framework skips the placeholder and selects the first option with a non-empty value attribute; the step records as PASSED"
    why_human: "Unit tests mock the Selenium Select layer; end-to-end wiring through the real Chrome/Edge driver and a live DOM requires a browser. Covers FV-01 smoke confirmation from 20-VALIDATION.md manual-only verification."
---

# Phase 20: first_valid Sentinel for select_by_index — Verification Report

**Phase Goal:** When a `type: select` / `action: select_by_index` element has `value: "first_valid"` (case-insensitive), the framework selects the first `<option>` whose `value` attribute is non-empty (skipping the leading placeholder), and raises `ElementActionError` if none qualify — numeric `select_by_index` unchanged.
**Verified:** 2026-06-07T14:37:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | D-01/D-02: `value.strip().lower() == "first_valid"` routes to `_select_first_valid_option`; numeric values still use `int(value)` | VERIFIED | `base_page.py` line 259: sentinel check before `int(value)` on line 262; confirmed by test run FV-01..FV-02 all passing |
| 2  | D-03: "validated" = non-empty post-strip `value` attribute; DOM order; first qualifier selected | VERIFIED | `_select_first_valid_option` iterates `sel.options`, returns on first `raw is not None and raw.strip()`; FV-09 confirms DOM-order short-circuit |
| 3  | D-04: whitespace-only / empty-string / None value attributes all treated as empty and skipped | VERIFIED | Line 282: `raw is not None and raw.strip()` guards all three cases; FV-03/FV-04/FV-05 pass |
| 4  | D-05: only `value` attribute considered — disabled state and visible text ignored | VERIFIED | Helper body reads only `opt.get_attribute("value")`; no `is_enabled()` or `.text` check in helper |
| 5  | D-06: no qualifying option raises `ElementActionError` with message matching "non-empty value attribute" | VERIFIED | Lines 289–291 raise `ElementActionError("No option with a non-empty value attribute found", element_name=name)`; FV-06 passes with `match="non-empty value attribute"` |
| 6  | Numeric `select_by_index` behavior is byte-for-byte unchanged (regression) | VERIFIED | `int(value)` path at line 262 untouched; FV-07 (`test_action_dispatch.py::TestElementActions::test_select_by_index`) passes; full 402-test unit suite green |
| 7  | `ElementActions.execute()` passes `"first_valid"` string unchanged to `select_dropdown` | VERIFIED | `element_actions.py` line 65: `self._page.select_dropdown(element.locator, "index", str(value), element.name)` — unmodified; FV-08 asserts exact call with `"first_valid"` and passes |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/unit/test_base_page_select_first_valid.py` | Unit coverage for FV-01..FV-06, FV-08, FV-09; contains `class TestSelectFirstValid` | VERIFIED | File exists; 8 test methods confirmed by `grep -c "def test_"`; class `TestSelectFirstValid` present; all 8 tests pass |
| `src/ui/base_page.py` | Sentinel branch in `select_dropdown` + `_select_first_valid_option` helper | VERIFIED | `_select_first_valid_option` appears at lines 260 (call site) and 266 (definition) — 2 occurrences as required; substantive implementation with option scan, None-guard, `opt.click()`, and `ElementActionError` raise |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `select_dropdown` index branch | `_select_first_valid_option` | `value.strip().lower() == "first_valid"` check at line 259, before `int(value)` at line 262 | WIRED | Sentinel check at line 259 short-circuits before `int()` cast; routing confirmed by FV-01 test exercising the full path |
| `_select_first_valid_option` | `ElementActionError` | `raise ElementActionError("No option with a non-empty value attribute found", element_name=name)` at lines 289–291 | WIRED | Raise shape mirrors the unknown-by raise at line 264; FV-06 passes with correct match string |

### Data-Flow Trace (Level 4)

Not applicable — this phase modifies a synchronous interaction helper that operates on live Selenium DOM state. There is no state variable rendered into JSX/TSX; data flows are exercised by unit mocks that accurately reflect the Selenium Select API contract.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| FV-01..FV-06, FV-08, FV-09 all pass | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py -v` | 8 passed in 0.52s | PASS |
| FV-07 regression (numeric index unchanged) | `.venv/bin/pytest tests/unit/test_action_dispatch.py::TestElementActions::test_select_by_index -x` | 1 passed in 0.43s | PASS |
| Full unit suite — zero regressions | `.venv/bin/pytest tests/unit/ -v --tb=no -q` | 402 passed in 0.77s | PASS |

### Probe Execution

No probe scripts declared or present for this phase. Step 7c: SKIPPED (no probe files under `scripts/*/tests/probe-*.sh`).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FV-01 | 20-01-PLAN.md | First non-empty-value option selected (options: None, "", "real") | SATISFIED | `test_selects_first_non_empty_value_option` passes |
| FV-02 | 20-01-PLAN.md | Sentinel matched case-insensitively ("FIRST_VALID", "First_Valid") | SATISFIED | `test_sentinel_case_insensitive` passes |
| FV-03 | 20-01-PLAN.md | Whitespace-only value attribute skipped | SATISFIED | `test_whitespace_value_skipped` passes |
| FV-04 | 20-01-PLAN.md | Empty-string value attribute skipped | SATISFIED | `test_empty_string_value_skipped` passes |
| FV-05 | 20-01-PLAN.md | None value attribute skipped without AttributeError | SATISFIED | `test_none_value_attribute_skipped` passes |
| FV-06 | 20-01-PLAN.md | No qualifying option raises `ElementActionError` with "non-empty value attribute" | SATISFIED | `test_no_valid_option_raises` passes |
| FV-07 | 20-01-PLAN.md | Numeric `select_by_index` regression — int() path unchanged | SATISFIED | `test_action_dispatch.py::TestElementActions::test_select_by_index` passes |
| FV-08 | 20-01-PLAN.md | `ElementActions.execute()` passes sentinel string unchanged to `select_dropdown` | SATISFIED | `test_dispatch_passes_sentinel_to_select_dropdown` passes |
| FV-09 | 20-01-PLAN.md | DOM-order scan: first qualifying option selected, not last | SATISFIED | `test_first_valid_in_dom_order` passes |

**Orphaned requirements check:** REQUIREMENTS.md does not exist at `.planning/REQUIREMENTS.md` — file is absent. All requirement IDs (FV-01..FV-09) are declared in the PLAN frontmatter and verified above. No orphaned IDs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, or `PLACEHOLDER` markers found in either modified file (`src/ui/base_page.py`, `tests/unit/test_base_page_select_first_valid.py`). No stub indicators (empty returns, hardcoded `[]`/`{}`/`null`). No `console.log`-only implementations.

### Human Verification Required

#### 1. End-to-End first_valid Selection Against a Live Browser

**Test:** Author a smoke workflow JSON with a `type: select`, `action: select_by_index`, `value: "first_valid"` element that targets a real `<select>` element on the app under test. The select must have at least one leading placeholder option with `value=""`. Run `pytest tests/smoke/ -v`.
**Expected:** The framework skips the placeholder option and selects the first `<option>` with a non-empty `value` attribute. The step result is recorded as PASSED, not as an `ElementActionError`.
**Why human:** Unit tests mock the entire Selenium `Select` layer. The end-to-end path through the real Chrome/Edge WebDriver, a live DOM rendering from the app, and the full workflow execution engine requires a browser. This is the "Manual-Only Verification" item explicitly documented in `20-VALIDATION.md`.

---

## Gaps Summary

No gaps. All 7 observable truths are VERIFIED in the codebase with direct test execution evidence. The single human verification item is an optional smoke confirmation for an already-proven unit-tested behavior, not a missing implementation. The phase goal is fully achieved at the code level.

---

_Verified: 2026-06-07T14:37:00Z_
_Verifier: Claude (gsd-verifier)_
