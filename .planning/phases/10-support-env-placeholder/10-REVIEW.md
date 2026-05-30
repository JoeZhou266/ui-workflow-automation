---
phase: 10-support-env-placeholder
reviewed: 2026-05-29T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/actions/value_resolver.py
  - src/core/config.py
  - tests/unit/test_value_resolver.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-05-29
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files were reviewed for the Phase 10 `${env:KEY}` placeholder feature: the value resolver module, the app config, and the unit test suite. The core implementation is correct — `configure_env_resolver()` populates a module-level dict that `resolve_dynamic_value()` consults when it sees an `env:` prefix, and `AppConfig.__init__` wires the two together. The error message on unknown key (listing available keys) is a nice touch.

The main concerns are: (1) no input validation on `configure_env_resolver()` means passing `None` produces an opaque `TypeError` at resolution time rather than a clear error at configuration time; (2) the test suite for `TestEnvPlaceholder` has no teardown, leaving stale module-level state after the class runs; and (3) the entire raw YAML dict (including potential credentials) is passed verbatim to `configure_env_resolver()`, which is a design concern worth documenting explicitly.

---

## Warnings

### WR-01: `configure_env_resolver()` accepts `None` — crashes with opaque error at call site

**File:** `src/actions/value_resolver.py:54-65`
**Issue:** `configure_env_resolver(data: dict)` has no runtime guard against `data` being `None`. If called with `None` (directly or via a YAML file that returns `None` before the `or {}` guard), line 184 executes `env_key not in _ENV_CONFIG` which raises `TypeError: argument of type 'NoneType' is not iterable`. The error message does not indicate the real cause (the resolver was never configured).
**Fix:**
```python
def configure_env_resolver(data: dict) -> None:
    global _ENV_CONFIG
    if data is None:
        raise TypeError(
            "configure_env_resolver() requires a dict, got None. "
            "Ensure the YAML file is valid and non-empty."
        )
    _ENV_CONFIG = data
```

---

### WR-02: `TestEnvPlaceholder` has no teardown — leaves stale `_ENV_CONFIG` state after test class

**File:** `tests/unit/test_value_resolver.py:253-295`
**Issue:** Every test in `TestEnvPlaceholder` calls `configure_env_resolver({...})` to set module-level state, but there is no `teardown_method` or autouse fixture to reset `_ENV_CONFIG` to `{}` after the class completes. After the class finishes, `_ENV_CONFIG` holds whatever the last test set (e.g., `{"base_url": "http://test.example.com"}`). Any future test that later resolves `${env:base_url}` in the same process will receive this stale value without being told where it came from. Test ordering changes (e.g., via `-p no:randomly`) can silently change behavior.
**Fix:** Add a class-level fixture (or `setup_method`/`teardown_method`) that resets state:
```python
class TestEnvPlaceholder:
    def setup_method(self):
        configure_env_resolver({})   # start each test with a clean slate

    def teardown_method(self, _method):
        configure_env_resolver({})   # leave module state clean for other tests
    ...
```

---

### WR-03: `_generate_sin_full()` uses `random` while `generate_random_number()` uses `secrets`

**File:** `src/actions/value_resolver.py:68-84`
**Issue:** `generate_random_number()` (line 36) uses `secrets.randbelow()` for unbiased cryptographic randomness. `_generate_sin_full()` (lines 70-73) uses `random.randint()`, which is a PRNG seeded from system time. This inconsistency means SIN numbers are weaker-randomness test data than random numbers. While neither value is used for security-sensitive purposes here, mixing randomness sources silently is confusing and could matter if the framework is ever used in a security-adjacent context.
**Fix:**
```python
import secrets

def _generate_sin_full() -> str:
    first = secrets.randbelow(8) + 1          # 1..8
    rest = [secrets.randbelow(10) for _ in range(7)]
    ...
```

---

### WR-04: Full raw YAML dict (including credentials) is passed to `configure_env_resolver()` without documentation

**File:** `src/core/config.py:33-34` and `src/actions/value_resolver.py:54-65`
**Issue:** `AppConfig.__init__` passes the entire `self._data` dict (the raw YAML) to `configure_env_resolver()`. This means every key in `env.*.yaml` — including `base_url`, `browser`, and any passwords or API keys stored there — becomes accessible from workflow JSON via `${env:KEY}`. There is no allowlist or denylist. If a workflow JSON authored by a less-trusted party uses `${env:some_credential}`, the value is silently embedded in the resolved output (e.g., typed into a form field). The CLAUDE.md constraint says credentials must come from `configs/env.*.yaml` or `.env`, but it does not address whether workflow JSON may reference them.
**Fix (documentation):** Add an explicit docstring warning to `configure_env_resolver()`:
```python
def configure_env_resolver(data: dict) -> None:
    """...
    Warning:
        All keys in *data* become accessible to workflow JSON authors via
        ``${env:KEY}``.  Do not store secrets in the YAML config that
        should not be embeddable in workflow output.
    """
```
**Fix (enforcement, if stricter control is desired):** Accept an allowlist parameter or a separate `workflow_vars` sub-dict in the YAML rather than passing the full config.

---

## Info

### IN-01: `test_configure_env_resolver_callable` is a vacuous test

**File:** `tests/unit/test_value_resolver.py:293-295`
**Issue:** This test asserts `callable(configure_env_resolver)`. That is trivially true for any imported function and cannot fail unless the import itself fails (which would already break every other test in the module). The test provides no coverage value.
**Fix:** Remove the test, or replace it with a meaningful assertion such as verifying that calling `configure_env_resolver({})` leaves `_ENV_CONFIG` empty and that a subsequent `${env:anything}` raises `ValueError`.

---

### IN-02: `generate_random_number()` missing type annotation on `length` parameter

**File:** `src/actions/value_resolver.py:34`
**Issue:** All other functions in the module are fully annotated. `generate_random_number(length = 7)` omits the type for `length`, and has a style inconsistency (space before `=` in default argument, which is non-idiomatic PEP 8).
**Fix:**
```python
def generate_random_number(length: int = 7) -> str:
```

---

### IN-03: `_sin_state` shared global not reset between test classes — order-dependent SIN chunk behavior

**File:** `src/actions/value_resolver.py:42-45` / `tests/unit/test_value_resolver.py`
**Issue:** `_sin_state` is module-level. Tests in `TestGenerators`, `TestPlaceholderRegistry`, `TestValueResolverIntegration`, and `TestEnvPlaceholder` all call `generate_sin_number()` (or `resolve_dynamic_value("${sin_number}")`) at various points. Because the state is global, the chunk counter can be mid-cycle when a test starts. Currently the tests call it in triples and the guard at line 100 (`call_count >= 3`) resets correctly, so there is no active bug. However if any future test calls `generate_sin_number()` an odd number of times (e.g., testing a single chunk), subsequent tests receive a mid-cycle SIN. Adding a `setup_method` reset in each test class that uses SIN generation would prevent this fragility.
**Fix:** For tests that need a fresh SIN, call `generate_sin_number()` 3 times (to exhaust the current SIN) before the assertions, or expose a `_reset_sin_state()` helper in the module for test use only.

---

_Reviewed: 2026-05-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
