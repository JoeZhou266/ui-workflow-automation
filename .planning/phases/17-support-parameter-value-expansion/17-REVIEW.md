---
phase: 17-support-parameter-value-expansion
reviewed: 2026-06-02T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/actions/value_resolver.py
  - src/actions/action_factory.py
  - src/workflow/workflow_engine.py
  - tests/unit/test_value_resolver.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-06-02
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 17 adds workflow parameter value expansion (`${param_name}` in element values) via three coordinated changes: `resolve_dynamic_value` gains an optional `params` kwarg, `ValueResolver` stores params at construction time, and `WorkflowEngine` builds a `self._params` dict from the declared parameters and injects it into each `ActionFactory`. The architecture is sound and the 10 new VP tests provide good coverage. One warning-level inconsistency was found in the params truthiness check in `resolve_dynamic_value`, plus three minor info-level findings.

---

## Warnings

### WR-01: Truthiness check on `params` silently skips non-None empty dict in resolution path

**File:** `src/actions/value_resolver.py:201`

**Issue:** The resolution guard uses `if params and key in params:`, which treats an empty dict `{}` as falsy. An explicitly provided empty `params={}` takes a different code path than `params={"some_key": "v"}`, but both should behave as "params was provided; check if key is present." For an empty dict `key in {}` is always `False` so there is no observable behavioral difference today — but this is inconsistent with the error-message branch on line 206 (`if params is not None`) which correctly distinguishes `None` from `{}`. If a future caller passes `params={}` expecting exact `is not None` semantics throughout the function, the mismatch could introduce subtle bugs when the function is extended.

**Fix:**
```python
# Before (line 201)
if params and key in params:

# After — consistent with the error-path check on line 206
if params is not None and key in params:
```

---

## Info

### IN-01: Unused `Optional` import in `workflow_engine.py`

**File:** `src/workflow/workflow_engine.py:4`

**Issue:** `from typing import Optional` is imported but `Optional` is never referenced in the file body. The codebase already uses `from __future__ import annotations`, and all type hints in this file use bare syntax or are absent. The unused import adds noise.

**Fix:** Remove the import:
```python
# Delete line 4:
from typing import Optional
```

### IN-02: `_sin_state` module-level mutable state is not reset between tests

**File:** `tests/unit/test_value_resolver.py` (affects `src/actions/value_resolver.py:42-44`)

**Issue:** `_sin_state` is a module-level dict that tracks the current SIN and call count across chunk calls. Tests in `TestGenerators`, `TestPlaceholderRegistry`, `TestValueResolverIntegration`, `TestEnvPlaceholder`, and the new `TestParamExpansion` (VP-03) all call `generate_sin_number()` / `resolve_dynamic_value("${sin_number}")` without resetting the shared state between test classes. VP-03 in particular makes a single call and checks only that the result is a 3-digit string, so it silently consumes one chunk from whatever SIN cycle is in progress at that point. If pytest execution order ever places VP-03 between two of the three calls that were intended to assemble a contiguous SIN in another test, that other test's Luhn-validity assertion would fail with a non-contiguous SIN.

**Fix:** Add a `setup_method` or autouse fixture to reset `_sin_state` between tests that rely on SIN chunk ordering:
```python
from src.actions.value_resolver import _sin_state

@pytest.fixture(autouse=True)
def reset_sin_state():
    _sin_state["current_sin"] = None
    _sin_state["call_count"] = 0
    yield
    _sin_state["current_sin"] = None
    _sin_state["call_count"] = 0
```

### IN-03: `ActionFactory` instantiated per element rather than per section

**File:** `src/workflow/workflow_engine.py:132`

**Issue:** `ActionFactory(section, self._wm, params=self._params)` is constructed inside `_run_element`, which is called once per element. This means a new `ValueResolver` object (and the `params or {}` copy) is allocated for every element in the workflow. For workflows with hundreds of elements this is unnecessary object churn. The factory could be constructed once in `_run_section` and reused across the elements in that section, since `section` and `self._wm` are constant within a section iteration.

**Fix (optional refactor):**
```python
def _run_section(self, section: SectionDefinition, ctx: ExecutionContext) -> None:
    logger.info("[Section] %s", section.name)
    dyn_section = DynamicSection(self._driver, self._wm, section, self._screenshots)
    factory = ActionFactory(dyn_section, self._wm, params=self._params)  # once per section
    for element in section.elements:
        self._run_element(element, factory, ctx.at_element(element.name))

def _run_element(
    self,
    element: ElementDefinition,
    factory: ActionFactory,          # accept pre-built factory
    ctx: ExecutionContext,
) -> None:
    ...
    # remove: factory = ActionFactory(section, self._wm, params=self._params)
```

---

_Reviewed: 2026-06-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
