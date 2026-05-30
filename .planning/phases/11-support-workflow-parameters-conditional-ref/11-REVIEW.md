---
phase: 11-support-workflow-parameters-conditional-ref
reviewed: 2026-05-29T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/data/condition_evaluator.py
  - src/models/workflow_models.py
  - src/data/json_loader.py
  - tests/unit/test_workflow_params.py
findings:
  critical: 0
  warning: 4
  info: 2
  total: 6
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-05-29T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

This phase adds workflow-level `parameters` with `${env:KEY}` resolution and conditional `$ref` nodes. The core logic in `condition_evaluator.py` and `workflow_models.py` is clean and well-structured. Four warning-level issues were identified in `json_loader.py`: a mutable default argument anti-pattern, unguarded `ValueError` propagation from `resolve_dynamic_value` at two call sites, inconsistent error wrapping in `load_raw()`, and unsafe raw-dict access on the `parameters` array before Pydantic validation runs. Two info-level issues cover a fragile test match string and a missing edge-case test.

## Warnings

### WR-01: Mutable default argument `params: dict = {}` in `resolve_refs`

**File:** `src/data/json_loader.py:20`
**Issue:** Using a mutable dict literal `{}` as a default argument is a classic Python footgun. Although `resolve_refs` does not mutate `params` in its current implementation, any future change that adds a write (e.g., merging inherited params) would silently share state across all callers that rely on the default. Python evaluates defaults once at function-definition time, so the same dict object is reused for every call that omits the argument.
**Fix:**
```python
# Change the signature from:
def resolve_refs(
    data: object,
    base_dir: Path,
    _resolving: frozenset = frozenset(),
    params: dict = {},
) -> object:

# To:
def resolve_refs(
    data: object,
    base_dir: Path,
    _resolving: frozenset = frozenset(),
    params: dict | None = None,
) -> object:
    if params is None:
        params = {}
```

---

### WR-02: `ValueError` from `resolve_dynamic_value` escapes `WorkflowValidationError` wrapping in `load()`

**File:** `src/data/json_loader.py:119-122`
**Issue:** The loop that extracts and resolves `${env:KEY}` parameter values (lines 119-122) sits *outside* the `try/except (FileNotFoundError, ValueError)` block that starts at line 124. If `resolve_dynamic_value` raises `ValueError` (unknown env key, or unknown placeholder token), it propagates to the caller as a raw `ValueError` rather than the typed `WorkflowValidationError` that the framework contract promises. Callers expecting only `WorkflowValidationError` on load failure will see an unhandled exception.
**Fix:**
```python
# Wrap the param-extraction loop inside a try/except, or expand the existing one:
        params: dict = {}
        raw_params = data.get("parameters") if isinstance(data, dict) else None
        if raw_params:
            try:
                for p in raw_params:
                    resolved_value = resolve_dynamic_value(p["value"])
                    params[p["name"]] = resolved_value
            except (ValueError, KeyError, TypeError) as exc:
                raise WorkflowValidationError(
                    f"Error resolving workflow parameters: {exc}", path=str_path
                ) from exc
```

---

### WR-03: `load_raw()` does not wrap `ValueError` or `WorkflowValidationError` from `resolve_refs` / `resolve_dynamic_value`

**File:** `src/data/json_loader.py:151-165`
**Issue:** `load_raw()` catches only `(OSError, json.JSONDecodeError)`. However, `resolve_refs` can raise `ValueError` (circular reference) and `WorkflowValidationError` (undefined parameter in condition), and the param-extraction loop can raise `ValueError` (bad env key) or `KeyError`/`TypeError` (malformed param entry). All of these propagate as their raw types without being wrapped in `WorkflowValidationError`. This is inconsistent with `load()`, which wraps them. Any caller of `load_raw()` that expects a uniform error type will not catch these.
**Fix:**
```python
    @staticmethod
    def load_raw(path: Union[str, Path]) -> dict:
        """Load a JSON file, resolve $ref references, and return the raw dict."""
        file_path = Path(path)
        str_path = str(file_path)
        try:
            raw = file_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            params: dict = {}
            raw_params = data.get("parameters") if isinstance(data, dict) else None
            if raw_params:
                for p in raw_params:
                    resolved_value = resolve_dynamic_value(p["value"])
                    params[p["name"]] = resolved_value
            return resolve_refs(data, file_path.parent, params=params)
        except (OSError, json.JSONDecodeError, FileNotFoundError, ValueError,
                KeyError, TypeError) as exc:
            raise WorkflowValidationError(str(exc), path=str_path) from exc
        except WorkflowValidationError:
            raise  # Already typed — re-raise as-is
```

---

### WR-04: Unsafe raw-dict access on `parameters` array before Pydantic validation

**File:** `src/data/json_loader.py:120-122` and `src/data/json_loader.py:160-162`
**Issue:** The parameter-extraction loop accesses `p["name"]` and `p["value"]` as bare dict keys (lines 121-122 and 161-162) on raw JSON data that has not yet been passed through Pydantic. If a `parameters` entry is not a dict (e.g., `null`, a string, or a list in a malformed JSON file), Python raises `TypeError`. If it is a dict but is missing the `"name"` or `"value"` key, Python raises `KeyError`. These surface as untyped exceptions rather than `WorkflowValidationError`. This is particularly relevant because the extraction runs *before* Pydantic's schema validation.
**Fix:**
```python
for p in raw_params:
    if not isinstance(p, dict) or "name" not in p or "value" not in p:
        raise WorkflowValidationError(
            f"Each entry in 'parameters' must be an object with 'name' and 'value' keys; "
            f"got: {p!r}",
            path=str_path,
        )
    resolved_value = resolve_dynamic_value(p["value"])
    params[p["name"]] = resolved_value
```

## Info

### IN-01: Test match string `"missing"` in `test_undefined_param_raises` is coincidental

**File:** `tests/unit/test_workflow_params.py:70`
**Issue:** The `pytest.raises(WorkflowValidationError, match="missing")` assertion works correctly — but only because the undefined parameter is named `"missing"`, which happens to appear literally in the error message (`"Condition references undefined parameter 'missing'..."`). If the parameter were renamed to anything else, the test would still pass regex-matching on the wrong substring. To make intent explicit, the match string should target a stable, parameter-name-independent fragment of the error message.
**Fix:**
```python
# Use a fragment that is always present regardless of the param name:
with pytest.raises(WorkflowValidationError, match="undefined parameter"):
    evaluate_condition("${missing} == 'x'", {})
```

---

### IN-02: No test for conditional `$ref` on a non-list dict value (returns `None` in dict)

**File:** `tests/unit/test_workflow_params.py`
**Issue:** The `resolve_refs` docstring documents that returning `None` for a false-condition `$ref` is only meaningful when the `$ref` is a list item (the list branch filters `None` values). If a `$ref` with a false condition appears as a *dict value* (e.g., `{"load_criteria": {"$ref": "...", "condition": "..."} }`), `resolve_refs` returns `None` for that key, which is preserved in the dict comprehension as `{..., "load_criteria": None, ...}`. This `None` then reaches Pydantic. Whether Pydantic accepts or rejects it depends on the field's `Optional` annotation. There is no test covering this edge case, so the behavior is undocumented and untested.
**Fix:** Add a test that places a `$ref` with a false condition as a dict value (not a list item) and asserts the resulting behavior — either that it is accepted by Pydantic (because the field is `Optional`) or that a clear error is raised.

---

_Reviewed: 2026-05-29T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
