---
phase: 05-support-wait-seconds
reviewed: 2026-05-26T01:33:22Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - tests/unit/test_wait_manager.py
  - src/core/enums.py
  - src/waits/wait_manager.py
  - tests/unit/test_workflow_models.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-05-26T01:33:22Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 5 adds `WaitConditionType.WAIT_SECONDS` to the enum, a `_sleep_seconds()` helper on `WaitManager`, and routes `WAIT_SECONDS` in `_dispatch()` to that helper. The implementation is well-structured and respects the CLAUDE.md synchronization-layer contract: the sleep is isolated in a single helper, logged at WARNING, and commented.

Two logic issues deserve attention. First, the `wait_for_condition()` method runs its four pre-checks (document ready, AJAX idle, spinner gone, overlay gone) unconditionally before branching to `_dispatch()`. When the condition is `WAIT_SECONDS` those checks will fire if the caller sets those flags, burning additional time and issuing spurious Selenium calls against a MagicMock/real driver — this is likely unintentional. Second, the model-validation tests assert that `timeout=0` raises `ValidationError`, but the model constraint is `ge=1` (greater-than-or-equal to 1), so `timeout=0` does correctly raise. However, the upper-bound test asserts that `timeout=301` raises, and the model constraint is `le=300`, so that too is correct. The tests themselves are sound for these cases; the real concern is the silent pre-check issue in the implementation.

The info item is a test-redundancy observation: two of the six `TestWaitSecondsDispatch` tests (`test_wait_seconds_as_pre_wait_simulates_pre_wait_call` and `test_wait_seconds_as_post_wait_simulates_post_wait_call`) are functionally identical to `test_wait_seconds_calls_time_sleep_with_timeout` — they only differ in the `element_name` string passed and do not exercise any additional code path.

## Warnings

### WR-01: WAIT_SECONDS does not short-circuit pre-dispatch readiness checks

**File:** `src/waits/wait_manager.py:89-122`
**Issue:** `wait_for_condition()` runs four pre-checks unconditionally before calling `_dispatch()`:

1. `require_document_ready` (line 94) — fires a `WebDriverWait` poll
2. `require_ajax_idle` (line 101) — fires a `WebDriverWait` poll
3. `spinner_locator` (line 110) — fires `_wait_gone()` with a `WebDriverWait`
4. `overlay_locator` (line 112) — fires `_wait_gone()` with a `WebDriverWait`

These flags default to `False`/`None` on `WaitConditionDefinition`, so they are harmless in normal use. However, a workflow author who sets `require_document_ready: true` alongside `condition: wait_seconds` will trigger a document-ready poll *in addition to* the intended sleep — which is unexpected behavior for a pure fixed-delay pause. More concretely, if the AUT is not loaded at all at the time of the pause (e.g., the pause is used before page navigation), the document-ready check can raise `WaitTimeoutError` and abort the step before the sleep even runs.

**Fix:** Add an early-return guard at the top of `wait_for_condition()` for `WAIT_SECONDS`, skipping all pre-checks:

```python
def wait_for_condition(
    self,
    condition_def: WaitConditionDefinition,
    element_name: str = "",
) -> None:
    ctype = condition_def.condition
    t = condition_def.timeout
    p = condition_def.poll_frequency_ms

    # WAIT_SECONDS is a pure fixed-delay pause — bypass all readiness
    # pre-checks (document ready, AJAX idle, spinner/overlay gone) because
    # they are not meaningful for an unconditional sleep and could raise
    # WaitTimeoutError before the sleep executes.
    if ctype == WaitConditionType.WAIT_SECONDS:
        self._sleep_seconds(t)
        return

    # Optional document/AJAX readiness checks first
    if condition_def.require_document_ready:
        ...
```

---

### WR-02: `_sleep_seconds` type annotation accepts `int` but `time.sleep` safely accepts `float` — annotation is unnecessarily restrictive for a public-facing helper

**File:** `src/waits/wait_manager.py:192`
**Issue:** `_sleep_seconds(self, seconds: int)` accepts only `int`. The `timeout` field on `WaitConditionDefinition` is typed as `int` (field constraint), so this does not cause a runtime bug today. However, `time.sleep` accepts `float`, and if `timeout` is ever widened to support fractional seconds (a natural future extension), callers will pass a `float` to a helper annotated as `int`, producing a type-checker error at that point. More urgently, the type annotation is slightly misleading — the helper comment says "configurable" and the CLAUDE.md says the sleep helper must be "configurable," implying future float support. The annotation is not a bug, but it is unnecessarily rigid.

**Fix:** Widen the annotation to `Union[int, float]` (or `float` since every `int` is a valid `float`):

```python
def _sleep_seconds(self, seconds: float) -> None:
    # Intentional fixed-duration pause — this IS the feature, not a timing workaround.
    # Per CLAUDE.md §Synchronization layer: sleep must be isolated in one helper,
    # configurable, logged at WARNING, and commented with the reason.
    logger.warning(
        "Sleeping for %ss (wait_seconds — intentional fixed-delay pause)", seconds
    )
    time.sleep(seconds)
```

Note: the format specifier changes from `%d` to `%s` (or `%g`) to correctly render a float if one is ever passed — `%d` applied to a float silently truncates in Python's `%`-style formatting.

---

## Info

### IN-01: Two test cases are redundant duplicates of an existing test

**File:** `tests/unit/test_wait_manager.py:67-83`
**Issue:** `test_wait_seconds_as_pre_wait_simulates_pre_wait_call` (line 67) and `test_wait_seconds_as_post_wait_simulates_post_wait_call` (line 76) exercise exactly the same code path as `test_wait_seconds_calls_time_sleep_with_timeout` (line 25). All three:

- Construct a `WaitConditionDefinition(condition=WAIT_SECONDS, timeout=N)`
- Call `wm.wait_for_condition(cdef, element_name=...)`
- Assert `mock_sleep.assert_called_once_with(N)`

The only difference is the `element_name` string and the value of `N`. The `element_name` argument affects only the `desc` string passed to `_dispatch()`, which is never used for `WAIT_SECONDS` (the branch calls `_sleep_seconds(timeout)` directly). These two tests add no coverage beyond what the first test already provides.

**Fix:** Remove or repurpose them. If the intent is to document that `wait_for_condition` works when called from the `pre_wait` and `post_wait` call sites in `ActionFactory`, a comment on the first test is sufficient. Alternatively, convert them into integration-level tests that verify the `action_factory → wait_manager` call chain.

---

_Reviewed: 2026-05-26T01:33:22Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
