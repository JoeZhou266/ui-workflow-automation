---
phase: 04-support-dynamic-placeholder-expansion
reviewed: 2026-05-19T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - tests/unit/test_value_resolver.py
  - src/actions/value_resolver.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-05-19
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the dynamic placeholder expansion implementation (`src/actions/value_resolver.py`) and its unit test suite (`tests/unit/test_value_resolver.py`).

The implementation is well-structured: the regex is correctly anchored, the Luhn check-digit computation is correct, and `ValueResolver.resolve` properly guards non-string types. The test coverage is solid for the happy path and the main passthrough cases.

Two warnings were found: a missing type guard in the public `resolve_dynamic_value` function that can raise `TypeError` on non-string input, and a gap in test coverage for that same path. Two info-level items cover a minor style issue and a missing edge-case test for the empty-braces token `${}`.

---

## Warnings

### WR-01: `resolve_dynamic_value` has no guard against non-string input

**File:** `src/actions/value_resolver.py:95`
**Issue:** `resolve_dynamic_value(value: str)` calls `_PLACEHOLDER_PATTERN.match(value)` directly. `re.Pattern.match()` raises `TypeError: expected string or bytes-like object` when passed a non-string (e.g., `None`, `int`, `list`). `ValueResolver.resolve` is correctly guarded with `isinstance(value, str)`, but `resolve_dynamic_value` is also exported in the package's public API and could be called directly by future callers or from tests without that guard. There is no test covering this error path.

**Fix:** Add a type guard at the top of `resolve_dynamic_value`:

```python
def resolve_dynamic_value(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"resolve_dynamic_value expects a str, got {type(value).__name__!r}"
        )
    match = _PLACEHOLDER_PATTERN.match(value)
    ...
```

Alternatively, if non-string passthrough is intentional, update the type signature to `Any` and return non-strings unchanged (mirroring `ValueResolver.resolve`). The current type annotation `str` makes the guard the correct approach.

---

### WR-02: Test suite missing coverage for non-string input to `resolve_dynamic_value`

**File:** `tests/unit/test_value_resolver.py` (after line 113)
**Issue:** `TestPlaceholderRegistry` tests `resolve_dynamic_value` for string inputs only. There is no test asserting the behavior when a non-string is passed (either `TypeError` if WR-01 guard is added, or the current unguarded crash). Without this test, a future refactor that accidentally removes the `isinstance` guard in `ValueResolver.resolve` and falls through to `resolve_dynamic_value` would not be caught.

**Fix:** Add a test (after `test_unknown_placeholder_raises`):

```python
def test_non_string_input_raises_type_error(self):
    with pytest.raises(TypeError):
        resolve_dynamic_value(None)  # type: ignore[arg-type]

def test_non_string_int_raises_type_error(self):
    with pytest.raises(TypeError):
        resolve_dynamic_value(42)  # type: ignore[arg-type]
```

These tests should be added after WR-01's guard is implemented.

---

## Info

### IN-01: `test_sin_first_digit` uses string membership check instead of a set

**File:** `tests/unit/test_value_resolver.py:47`
**Issue:** `generate_sin_number()[0] in "12345678"` performs a substring search on a string rather than a membership test against a set. This works correctly for single-character strings but is semantically ambiguous — a reader must verify that `"1"` in `"12345678"` is a single-char match, not a multi-char substring match.

**Fix:** Use a set for clarity:

```python
assert generate_sin_number()[0] in {"1", "2", "3", "4", "5", "6", "7", "8"}
```

Or equivalently:

```python
assert generate_sin_number()[0] in set("12345678")
```

---

### IN-02: No test for the empty-braces edge case `${}`

**File:** `tests/unit/test_value_resolver.py` (after line 109)
**Issue:** The regex `[^}]+` requires at least one character inside `${}`. An input of `"${}"` does not match the pattern and is returned as-is (passthrough). This is correct behavior but is untested. If the regex were ever changed to `[^}]*` (zero or more), `"${}"` would match and raise `ValueError: Unknown placeholder`. A test would prevent this regression.

**Fix:** Add a passthrough test:

```python
def test_passthrough_empty_braces(self):
    # "${}" does not match the placeholder pattern (requires 1+ chars inside braces)
    assert resolve_dynamic_value("${}") == "${}"
```

---

_Reviewed: 2026-05-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
