---
phase: 11-support-workflow-parameters-conditional-ref
fixed_at: 2026-05-30T00:00:00Z
review_path: .planning/phases/11-support-workflow-parameters-conditional-ref/11-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-05-30T00:00:00Z
**Source review:** .planning/phases/11-support-workflow-parameters-conditional-ref/11-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (WR-01, WR-02, WR-03, WR-04; IN-* excluded by fix_scope=critical_warning)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: Mutable default argument `params: dict = {}` in `resolve_refs`

**Files modified:** `src/data/json_loader.py`
**Commit:** c236e47
**Applied fix:** Changed function signature from `params: dict = {}` to `params: dict | None = None` and added `if params is None: params = {}` guard at the top of the function body (after the docstring). The `from __future__ import annotations` at the top of the file makes the `dict | None` union syntax safe on Python 3.9.

---

### WR-02: `ValueError` from `resolve_dynamic_value` escapes `WorkflowValidationError` wrapping in `load()`

**Files modified:** `src/data/json_loader.py`
**Commit:** e47ebca
**Applied fix:** Wrapped the param-extraction loop in `load()` in its own `try/except` block that catches `(ValueError, KeyError, TypeError)` and re-raises as `WorkflowValidationError`. A preceding `except WorkflowValidationError: raise` guard ensures already-typed errors pass through unchanged. This was combined with the WR-04 type guard (see below) in a single atomic commit.

---

### WR-03: `load_raw()` does not wrap `ValueError` or `WorkflowValidationError` from `resolve_refs` / `resolve_dynamic_value`

**Files modified:** `src/data/json_loader.py`
**Commit:** 9e0d20e
**Applied fix:** Expanded the `except` clause in `load_raw()` from `(OSError, json.JSONDecodeError)` to also cover `FileNotFoundError`, `ValueError`, `KeyError`, and `TypeError`. Added a preceding `except WorkflowValidationError: raise` clause so already-typed errors are re-raised as-is without double-wrapping. Also introduced a local `str_path` variable (matching the pattern in `load()`) so the `path=` argument to `WorkflowValidationError` is available. This was combined with the WR-04 type guard for `load_raw()` in a single atomic commit.

---

### WR-04: Unsafe raw-dict access on `parameters` array before Pydantic validation

**Files modified:** `src/data/json_loader.py`
**Commit:** e47ebca (load()), 9e0d20e (load_raw())
**Applied fix:** Added a type/key guard before accessing `p["name"]` / `p["value"]` in both `load()` and `load_raw()`:
```python
if not isinstance(p, dict) or "name" not in p or "value" not in p:
    raise WorkflowValidationError(
        f"Each entry in 'parameters' must be an object with 'name' and 'value' keys; "
        f"got: {p!r}",
        path=str_path,
    )
```
This converts silent `KeyError`/`TypeError` on malformed parameter entries into an informative `WorkflowValidationError` before Pydantic runs.

---

_Fixed: 2026-05-30T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
