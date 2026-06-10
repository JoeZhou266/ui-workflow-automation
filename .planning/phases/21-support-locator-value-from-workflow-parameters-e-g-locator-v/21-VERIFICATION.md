---
phase: 21-support-locator-value-from-workflow-parameters-e-g-locator-v
verified: 2026-06-10T00:59:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 21: Support Locator Value from Workflow Parameters — Verification Report

**Phase Goal:** A locator's `value` may embed `${param}` tokens (full-value or inside an XPath/CSS string, e.g. `//div[@id='${company_code}']`, `#row-${id}`) that are resolved from the workflow `params` block via a non-anchored expansion path; unknown tokens fail loud. Element-value anchored expansion is unchanged.
**Verified:** 2026-06-10T00:59:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | D-01: A locator value like `//div[@id='${company_code}']` is sent to the browser with company_code substituted from workflow params (partial/embedded expansion) | VERIFIED | `resolve_locator_params` in `value_resolver.py` lines 219-258 uses non-anchored `_LOCATOR_PARAM_PATTERN.sub(_replace, value)`; test `test_embedded_xpath_token` and `test_embedded_css_token` both PASS |
| 2 | D-02: Multiple `${param}` tokens in a single selector are all expanded via the non-anchored regex distinct from the anchored element-value pattern | VERIFIED | `_LOCATOR_PARAM_PATTERN = re.compile(r"\$\{([^}]+)\}")` at line 24 (non-anchored) is distinct from `_PLACEHOLDER_PATTERN = re.compile(r"^\$\{([^}]+)\}$")` at line 15 (anchored); `test_multiple_tokens_all_expanded` PASSES |
| 3 | D-04: Locator tokens resolve from the workflow params block only; `${env:KEY}` and dynamic generators are treated as unknown keys, never consulted | VERIFIED | `resolve_locator_params` calls `_LOCATOR_PARAM_PATTERN.sub(_replace, value)` where `_replace` only looks in `params` dict; no reference to `_ENV_CONFIG` or `PLACEHOLDER_REGISTRY` in that function; `test_unknown_token_full_value_raises` confirms env-style tokens raise ValueError |
| 4 | D-05: An unknown `${token}` in a locator raises ValueError naming the missing param and the step is recorded FAILED | VERIFIED | `_replace` closure raises `ValueError(f"Unknown locator param '${{{key}}}'. Workflow params: {sorted(params)}")` at line 252-255; `test_unknown_token_full_value_raises`, `test_unknown_token_embedded_raises`, `test_resolve_locator_unknown_token_raises` all PASS; ValueError propagates out of `ActionFactory.run` (no catch in run()) |
| 5 | D-03: Element value expansion uses the anchored pattern unchanged; `prefix_${name}` is not expanded (VP-09 regression guard holds) | VERIFIED | `_PLACEHOLDER_PATTERN` (anchored) unchanged at line 15; `resolve_dynamic_value` untouched; `test_partial_token_not_expanded` (VP-09) PASSES; full unit suite 417/417 passes |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/actions/value_resolver.py` | `resolve_locator_params` function + `_LOCATOR_PARAM_PATTERN` non-anchored regex | VERIFIED | Both present at lines 24 and 219; function is substantive (27 lines with docstring, inner closure, `re.sub` call); imported and called in `action_factory.py` |
| `src/actions/action_factory.py` | `self._params` storage + `_resolve_locator` helper wiring resolution into `run()` | VERIFIED | `self._params: dict = params or {}` at line 27; `_resolve_locator` at lines 29-50; `run()` calls `_resolve_locator(element.locator)` at line 72; `model_copy` at line 76 |
| `tests/unit/test_value_resolver.py` | `class TestResolveLocatorParams` covering LP-01..LP-05 | VERIFIED | Class exists at line 396; 10 test methods tagged LP-01..LP-05; all 10 PASS |
| `tests/unit/test_locator_resolver.py` | `class TestLocatorResolverWithParams` covering LP-06..LP-09 | VERIFIED | Class exists at line 78; 5 test methods covering LP-06..LP-09; all 5 PASS |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ActionFactory.run` | `resolve_locator_params` in `value_resolver.py` | `_resolve_locator()` called at top of `run()` before `skip_if_not_visible` probe | WIRED | `action_factory.py` line 72: `resolved_locator = self._resolve_locator(element.locator)`; line 47 in `_resolve_locator`: `from src.actions.value_resolver import resolve_locator_params` followed by call |
| `ActionFactory.run` | `ElementActions.execute` | resolved `ElementDefinition` (via `model_copy`) passed to `execute/_execute_with_retry` | WIRED | Lines 73-76 build `target` via `model_copy` when locator changed; lines 96-98 pass `target` to `_execute_with_retry` and `execute`; `test_run_passes_resolved_element_to_execute` (LP-09) confirms `executed_elements[0].locator.value == "ACME"` |

---

### Data-Flow Trace (Level 4)

Not applicable. This phase delivers a pure-function expansion engine (no UI rendering, no dynamic data source). The artifacts are utility functions and a wiring layer — data-flow trace applies to components that render state, not to resolver functions.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Embedded XPath token expands | `pytest tests/unit/test_value_resolver.py::TestResolveLocatorParams::test_embedded_xpath_token -q` | PASS | PASS |
| Embedded CSS token expands | `pytest tests/unit/test_value_resolver.py::TestResolveLocatorParams::test_embedded_css_token -q` | PASS | PASS |
| Unknown token raises ValueError | `pytest tests/unit/test_value_resolver.py::TestResolveLocatorParams::test_unknown_token_embedded_raises -q` | PASS | PASS |
| VP-09 regression guard: anchored path unchanged | `pytest tests/unit/test_value_resolver.py -k partial_token_not_expanded -q` | 1 PASSED | PASS |
| Full unit suite (417 tests, no regressions) | `pytest tests/unit/ -q` | 417 passed | PASS |
| run()-level resolved locator threads to execute | `pytest tests/unit/test_locator_resolver.py::TestLocatorResolverWithParams::test_run_passes_resolved_element_to_execute -q` | PASS | PASS |

---

### Probe Execution

Step 7c: No conventional `scripts/*/tests/probe-*.sh` probes exist and none declared in PLAN frontmatter. SKIPPED.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LP-01 | 21-01-PLAN.md (D-01) | Embedded XPath token expands | SATISFIED | `test_embedded_xpath_token` PASSES; `resolve_locator_params` uses non-anchored regex |
| LP-02 | 21-01-PLAN.md (D-01) | Embedded CSS token expands | SATISFIED | `test_embedded_css_token` PASSES |
| LP-03 | 21-01-PLAN.md (D-01) | Multiple tokens in one string all expanded | SATISFIED | `test_multiple_tokens_all_expanded` PASSES |
| LP-04 | 21-01-PLAN.md (D-01) | No-token string returned unchanged | SATISFIED | `test_no_token_unchanged` PASSES; identity returned by `_resolve_locator` via string equality check |
| LP-05 | 21-01-PLAN.md (D-05) | Unknown `${x}` raises ValueError naming the param | SATISFIED | `test_unknown_token_full_value_raises` + `test_unknown_token_embedded_raises` + `test_error_message_lists_available_keys` PASS |
| LP-06 | 21-01-PLAN.md (D-01/D-02) | `ActionFactory._resolve_locator` expands token from params | SATISFIED | `test_resolve_locator_expands_full_token` PASSES |
| LP-07 | 21-01-PLAN.md (D-03) | Locator with no params / no token returns identity (regression) | SATISFIED | `test_resolve_locator_no_params_returns_identity` + `test_resolve_locator_no_token_returns_identity` PASS |
| LP-08 | 21-01-PLAN.md (D-05) | `_resolve_locator` unknown token raises ValueError (fail-loud) | SATISFIED | `test_resolve_locator_unknown_token_raises` PASSES; empty-params early-exit removed (SUMMARY deviation #2) |
| LP-09 | 21-01-PLAN.md (D-01) | `ActionFactory.run` threads resolved ElementDefinition copy to executor | SATISFIED | `test_run_passes_resolved_element_to_execute` PASSES; `model_copy` confirmed in `run()` lines 73-76 |
| LP-EMBED-EXPAND (D-01) | 21-01-PLAN.md | Locator value supports partial/embedded `${param}` expansion | SATISFIED | Full test class `TestResolveLocatorParams` (10 tests) all PASS |
| LP-NONANCHORED (D-02) | 21-01-PLAN.md | Non-anchored regex distinct from anchored `_PLACEHOLDER_PATTERN` | SATISFIED | Two distinct patterns confirmed in `value_resolver.py` lines 15 and 24; `grep` count = 1 each |
| LP-LOCATOR-ONLY (D-03) | 21-01-PLAN.md | Element-value anchored behavior unchanged, no regression | SATISFIED | VP-09 PASSES; full 417-test suite PASSES; `element_actions.py` / `base_page.py` not in any of the 3 phase commits |
| LP-PARAMS-ONLY (D-04) | 21-01-PLAN.md | Tokens resolve from workflow params block only, no env/generators | SATISFIED | `resolve_locator_params` body: only `params` dict referenced; no `_ENV_CONFIG` / `PLACEHOLDER_REGISTRY` calls |
| LP-FAILLOUD (D-05) | 21-01-PLAN.md | Unknown `${token}` raises ValueError naming missing param | SATISFIED | ValueError raised immediately by `_replace` closure; no catch in `run()`; error message verified by test |

Note: `REQUIREMENTS.md` does not exist at `.planning/REQUIREMENTS.md`. Requirement IDs LP-01..LP-09 are defined inline in `21-RESEARCH.md` (lines 617-625) and `21-VALIDATION.md`. All 9 LP IDs plus the 5 PLAN frontmatter requirement aliases are accounted for above. No orphaned requirements detected.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | — |

Scan of all 4 modified files (`value_resolver.py`, `action_factory.py`, `test_value_resolver.py`, `test_locator_resolver.py`):
- No `TBD`, `FIXME`, or `XXX` markers found.
- No `TODO` or `HACK` markers found.
- No `return null / return {} / return []` stub patterns in production code.
- "PLACEHOLDER" occurrences in `value_resolver.py` are all variable/constant names (`_PLACEHOLDER_PATTERN`, `PLACEHOLDER_REGISTRY`) and inline docstring references — not debt markers.
- The non-string guard `if not isinstance(locator.value, str): return locator` in `_resolve_locator` is correctly not a stub — it is a type guard for mock-based unit tests (documented as SUMMARY deviation #1).

---

### Human Verification Required

None. All behaviors for this phase are pure-function assertions (input selector + params → expected resolved selector) fully exercised by the automated test suite. No visual, real-time, or external-service behavior was introduced.

---

### Gaps Summary

No gaps. All 5 must-have truths are VERIFIED. All 4 required artifacts exist and are substantive and wired. Both key links are confirmed WIRED with evidence at the code and test level. All LP-01..LP-09 requirements are SATISFIED. The full 417-test unit suite passes with no regressions.

The one intentional scope deferral — non-element locators (`pre_wait`/`post_wait` conditions, `load_criteria`, `spinner_locator`, `overlay_locator`) are not expanded in this phase — is correctly documented in the SUMMARY and does not affect the phase goal, which is scoped to `element.locator.value` only.

---

_Verified: 2026-06-10T00:59:00Z_
_Verifier: Claude (gsd-verifier)_
