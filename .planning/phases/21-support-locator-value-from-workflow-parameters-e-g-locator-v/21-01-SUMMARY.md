---
phase: 21-support-locator-value-from-workflow-parameters-e-g-locator-v
plan: "01"
subsystem: actions
tags: [locator-expansion, params, value-resolver, action-factory, tdd]
dependency_graph:
  requires: [phase-17-parameter-value-expansion]
  provides: [locator-param-expansion-LP-01-to-LP-09]
  affects: [src/actions/value_resolver.py, src/actions/action_factory.py]
tech_stack:
  added: []
  patterns:
    - Non-anchored regex (_LOCATOR_PARAM_PATTERN) for partial/embedded ${param} expansion in locator values
    - Upstream seam (option b): resolve locator params in ActionFactory.run before any probe/action
    - model_copy pattern for producing resolved ElementDefinition copies (pydantic v2)
    - Zero-allocation fast-path: return same locator object when value is unchanged
key_files:
  created: []
  modified:
    - src/actions/value_resolver.py
    - src/actions/action_factory.py
    - tests/unit/test_value_resolver.py
    - tests/unit/test_locator_resolver.py
decisions:
  - "Seam choice (option b): resolve element.locator upstream in ActionFactory.run rather than in LocatorResolver.resolve; lowest blast radius — only action_factory.py + value_resolver.py change"
  - "Non-anchored _LOCATOR_PARAM_PATTERN distinct from anchored _PLACEHOLDER_PATTERN: locator tokens may be embedded in CSS/XPath selectors (D-02)"
  - "model_copy for resolved ElementDefinition: ElementActions.execute reads element.locator internally at ~9 branches; a resolved copy is the only correct propagation path"
  - "Zero-allocation fast-path: when resolved_value == locator.value (no tokens), return the same LocatorDefinition object"
  - "Non-string locator value guard: isinstance check before regex allows MagicMock-based unit tests (VP-10) to continue passing"
  - "Deferred: non-element locators (pre_wait/post_wait conditions, load_criteria, spinner_locator, overlay_locator) not expanded — these flow through WaitManager/PageReadiness without params; acceptable per CONTEXT.md scope decision"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-10"
  tasks_completed: 3
  files_changed: 4
---

# Phase 21 Plan 01: Locator Value Param Expansion Summary

Parameterized locator support: `resolve_locator_params` + `_LOCATOR_PARAM_PATTERN` (non-anchored) added to `value_resolver.py`; `ActionFactory.run` resolves `element.locator` upstream via `_resolve_locator` and threads a `model_copy`-produced `ElementDefinition` to all probe and execution paths.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wave 0 — write failing locator-expansion tests | b4ede58 | tests/unit/test_value_resolver.py, tests/unit/test_locator_resolver.py |
| 2 | Add resolve_locator_params (non-anchored expansion) | 26868dd | src/actions/value_resolver.py |
| 3 | Wire locator resolution into ActionFactory.run | 05b72f6 | src/actions/action_factory.py |

## What Was Built

### `src/actions/value_resolver.py`

- Added `_LOCATOR_PARAM_PATTERN = re.compile(r"\$\{([^}]+)\}")` — non-anchored regex, distinct from the existing anchored `_PLACEHOLDER_PATTERN` (D-02). Placed immediately after the anchored pattern with a comment noting the distinction.
- Added `resolve_locator_params(value: str, params: dict) -> str` — module-level function placed after `resolve_dynamic_value` and before `class ValueResolver`. Uses `_LOCATOR_PARAM_PATTERN.sub(_replace, value)` where `_replace` raises `ValueError("Unknown locator param '${key}'. Workflow params: [...]")` for unknown keys. Resolves from `params` only; never references `_ENV_CONFIG` or `PLACEHOLDER_REGISTRY` (D-04).

### `src/actions/action_factory.py`

- Added `self._params: dict = params or {}` to `__init__` (mirrors `ValueResolver` convention).
- Added `LocatorDefinition` to the import from `src.models.workflow_models`.
- Added `_resolve_locator(self, locator: LocatorDefinition) -> LocatorDefinition` private helper. Returns same object when: locator value is non-string (guard for mock-based tests), or `resolved_value == locator.value` (no tokens — zero allocation). Otherwise returns `LocatorDefinition(by=locator.by, value=resolved_value)`.
- Updated `run()`: locator resolution happens at the TOP before the `skip_if_not_visible` probe. Builds `target = element.model_copy(update={"locator": resolved_locator})` when locator changed, otherwise `target = element`. All downstream calls (`is_visible`, `_execute_with_retry`, `execute`) use `target`. Element value resolution path (anchored `_PLACEHOLDER_PATTERN`) is unchanged (D-03).

### Tests

- `tests/unit/test_value_resolver.py`: Added `class TestResolveLocatorParams` (LP-01..LP-05, 10 tests): embedded XPath token, embedded CSS token, multiple tokens, adjacent text, full-value token, no-token unchanged, XPath quote context, unknown token (full-value), unknown token (embedded), error message with "Workflow params:".
- `tests/unit/test_locator_resolver.py`: Added `class TestLocatorResolverWithParams` (LP-06..LP-09, 7 tests): `_resolve_locator` with full token, identity return with empty params+no token, identity return with params+no token, unknown token ValueError, `run()`-level resolved element identity check.

## Verification Results

| Check | Result |
|-------|--------|
| `python -m pytest tests/unit/ -q` | 417/417 passed |
| `_PLACEHOLDER_PATTERN = re.compile` count in value_resolver.py | 1 (unchanged) |
| `_LOCATOR_PARAM_PATTERN = re.compile` count (non-comment) | 1 (added) |
| VP-09 `test_partial_token_not_expanded` | PASS (regression guard holds) |
| Files modified (git diff) | Only 4 planned files |
| element_actions.py / base_page.py unchanged | Confirmed |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] VP-10 regression: MagicMock locator value caused TypeError in _resolve_locator**
- **Found during:** Task 3 (first test run after implementation)
- **Issue:** The existing VP-10 test (`test_action_factory_integration`) uses `MagicMock()` for the full element, so `element.locator.value` is a `MagicMock`, not a string. `resolve_locator_params` passes this to `re.sub` which raises `TypeError: expected string or bytes-like object`.
- **Fix:** Added `if not isinstance(locator.value, str): return locator` guard at the top of `_resolve_locator`, before calling `resolve_locator_params`. This is also semantically correct — LocatorDefinition validates `value: str` at parse time, so non-string values only appear in test mocks.
- **Files modified:** src/actions/action_factory.py
- **Commit:** 05b72f6

**2. [Rule 1 - Bug] Early-exit on empty params masked unknown-token ValueError**
- **Found during:** Task 3 (LP-08 test failure)
- **Issue:** Initial implementation used `if not self._params: return locator` which short-circuits for `params={}`, preventing unknown-token errors from being raised (D-05 violated). The plan said "if `not self._params` return `locator` unchanged" but this conflicts with the requirement that unknown tokens must raise even when params is explicitly empty.
- **Fix:** Removed the empty-dict early-exit. The `resolve_locator_params` call itself correctly handles the case: for a locator with no tokens (no `${...}`), `re.sub` returns the original string unchanged and the identity check `resolved_value == locator.value` returns the same object; for a locator with unknown tokens and empty params, it raises ValueError as required.
- **Files modified:** src/actions/action_factory.py
- **Commit:** 05b72f6

## Deferred Items

Non-element locators (`pre_wait`/`post_wait` `WaitConditionDefinition.locator`, `LoadCriteria.locator`, `spinner_locator`, `overlay_locator`) are NOT expanded by this phase. These locators flow through `WaitManager` and `PageReadiness` without a params path. Acceptable per CONTEXT.md scope decision — a future phase can thread params through those layers if needed.

## Known Stubs

None. All functionality is fully wired end-to-end.

## Threat Flags

No new security-relevant surface introduced beyond what was modeled in the plan's threat register (T-21-01, T-21-02, T-21-03 all addressed). No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Self-Check: PASSED

- src/actions/value_resolver.py: FOUND (contains `def resolve_locator_params` and `_LOCATOR_PARAM_PATTERN`)
- src/actions/action_factory.py: FOUND (contains `_resolve_locator`, `model_copy`, `self._params`)
- tests/unit/test_value_resolver.py: FOUND (contains `class TestResolveLocatorParams`)
- tests/unit/test_locator_resolver.py: FOUND (contains `class TestLocatorResolverWithParams`)
- Commits: b4ede58, 26868dd, 05b72f6 — all exist in git log
