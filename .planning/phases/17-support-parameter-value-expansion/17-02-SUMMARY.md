---
plan: 17-02
phase: 17-support-parameter-value-expansion
status: complete
wave: 2
---

## Summary

Implemented parameter value expansion (GREEN phase) — three targeted source changes thread the workflow `parameters` dict from `WorkflowEngine` through `ActionFactory` into `ValueResolver`, enabling `${param_name}` tokens in element `value` fields to resolve to workflow-level parameter values at runtime.

## What Was Built

### Task 1: value_resolver.py

- `resolve_dynamic_value` gains `params: dict | None = None` kwarg
- Resolution order: `env:` → `PLACEHOLDER_REGISTRY` → `params` dict → `ValueError`
- Error message includes `"Workflow params: [keys]"` when params dict is provided
- `ValueResolver` gains `__init__(params: dict | None = None)` — stores `self._params`
- `_resolve_string` passes `params=self._params` through to `resolve_dynamic_value`
- Fully backwards-compatible: no-arg forms continue to work unchanged

### Task 2: action_factory.py

- Removed module-level `_resolver = ValueResolver()` singleton (prevents cross-workflow state contamination)
- `ActionFactory.__init__` now accepts `params: dict | None = None`
- Per-instance `self._resolver = ValueResolver(params=params)` created in `__init__`
- `run()` method updated to use `self._resolver.resolve(element.value)`

### Task 3: workflow_engine.py

- Added `from src.actions.value_resolver import resolve_dynamic_value` import
- `WorkflowEngine.__init__` builds `self._params: dict` by re-resolving `${env:KEY}` tokens in parameter values (pitfall guard: parameters like `{"name": "x", "value": "${env:VAR}"}` resolve to the actual env value, not the literal token)
- `_run_element` passes `params=self._params` to `ActionFactory`

## Verification Results

- `pytest tests/unit/test_value_resolver.py::TestParamExpansion -v` → **10 PASSED** (VP-01..VP-10 all green)
- `pytest tests/unit/test_value_resolver.py -v` → **54 PASSED** (all pre-existing + VP tests)
- `pytest tests/unit/ -v` → **382 PASSED** (full unit suite, no regressions)

## Key Files

### key-files.modified
- src/actions/value_resolver.py
- src/actions/action_factory.py
- src/workflow/workflow_engine.py

## Self-Check: PASSED

All acceptance criteria met:
- Singleton `_resolver = ValueResolver()` removed from action_factory.py ✓
- `self._resolver = ValueResolver(params=params)` present in ActionFactory ✓
- `resolve_dynamic_value(p.value)` re-resolution in WorkflowEngine ✓
- `ActionFactory(section, self._wm, params=self._params)` in _run_element ✓
- All 54 unit tests pass ✓
- Full unit suite (382 tests) green ✓
