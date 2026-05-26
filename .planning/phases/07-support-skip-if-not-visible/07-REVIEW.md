---
phase: 07-support-skip-if-not-visible
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/core/exceptions.py
  - src/actions/action_factory.py
  - src/workflow/workflow_engine.py
  - tests/unit/test_action_dispatch.py
  - tests/unit/test_result_collector.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-05-26T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the `skip_if_not_visible` feature implementation spanning the exception hierarchy, action factory, workflow engine, and unit tests. The overall design is sound: `SkipElementSignal` is raised as a control-flow sentinel, caught before the broader `ElementActionError` handler, and routed to `record_skip`. The unit tests in both test files are thorough and well-structured.

Two warnings were found, both in `workflow_engine.py`. The more serious one is a logic bug in `_infer_failure_phase` where the substring `"pre"` matches the wait condition name `"present"`, causing pre-wait timeouts that occur while waiting for a `PRESENT` condition to be mis-classified as `PRE_WAIT` phase rather than `ACTION` phase. The second is that the `SkipElementSignal` catch discards the signal's message (which includes the element name context) in favour of a hardcoded string, reducing skip record debuggability. One info item flags the semantic oddity of `SkipElementSignal` inheriting from `FrameworkError`.

## Warnings

### WR-01: `_infer_failure_phase` — `"pre"` substring matches `"present"` condition name

**File:** `src/workflow/workflow_engine.py:175`
**Issue:** The heuristic `"pre" in msg` is applied to the lowercased `WaitTimeoutError` message. A timeout while waiting for `WaitConditionType.PRESENT` produces a message like `"Wait timed out after 10s waiting for 'present'"`. The substring `"pre"` matches `"present"`, so the failure phase is mis-reported as `PRE_WAIT` even when the timeout occurred during the action phase (e.g., in a `post_wait` configured with `condition: present`). Similarly the check `"post" in msg` would match any condition or element name containing "post".

The `WaitTimeoutError.__init__` does not encode whether the wait was a pre_wait or post_wait — that context must be passed explicitly rather than inferred from message content.

**Fix:** Pass the phase explicitly to `_infer_failure_phase` (or to `record_fail` directly) from the call site in `ActionFactory.run`. One clean approach: let `WaitManager.wait_for_condition` accept an optional `phase` label, or tag the exception at the raise site. At minimum, narrow the heuristic to look for the literal labels used in log messages:

```python
@staticmethod
def _infer_failure_phase(exc: WaitTimeoutError) -> FailurePhase:
    msg = str(exc).lower()
    # Match only the explicit phase labels, not partial substrings of condition names.
    if "pre_wait" in msg:
        return FailurePhase.PRE_WAIT
    if "post_wait" in msg:
        return FailurePhase.POST_WAIT
    return FailurePhase.ACTION
```

Alternatively, propagate phase as a parameter through the exception or the call chain instead of parsing the message.

---

### WR-02: `SkipElementSignal` catch discards signal message; hardcoded reason loses element context already carried by the exception

**File:** `src/workflow/workflow_engine.py:135-138`
**Issue:** When `SkipElementSignal` is caught, `record_skip` is called with the hardcoded string `"skip_if_not_visible=true"` as the reason. The caught exception already carries a formatted message that includes the element name (e.g., `"Element not visible — skipping (element='submit_btn')"`) via `SkipElementSignal.__init__`. By ignoring the exception message, the skip record in the `ExecutionSummary` contains less context than it could. When multiple elements are skipped, all skip records look identical in the reason field, making post-run analysis harder.

```python
# Current — loses exception context:
except SkipElementSignal:
    self._collector.record_skip(
        ctx, element.action, reason="skip_if_not_visible=true"
    )

# Fix — preserve exception message:
except SkipElementSignal as exc:
    self._collector.record_skip(
        ctx, element.action, reason=str(exc)
    )
```

This is low-risk — `str(exc)` is already formatted safely by `SkipElementSignal.__init__` and the `reason` field is stored as a string in `StepResult.error_message`.

---

## Info

### IN-01: `SkipElementSignal` inherits from `FrameworkError` — control-flow signal in the error hierarchy

**File:** `src/core/exceptions.py:96`
**Issue:** `SkipElementSignal` is documented as "a control-flow signal, not an error" but inherits from `FrameworkError` (which inherits from `Exception`). As a sibling of `ElementActionError`, it will be caught by any bare `except FrameworkError` handler that might be added elsewhere in the future, potentially silencing skips where they should bubble. Python's `BaseException` (or a dedicated `SignalBase` class not in the `Exception` hierarchy) is the conventional base for non-error control-flow. The current design works correctly for the existing catch hierarchy in `workflow_engine.py` (because `SkipElementSignal` is caught first), but the inheritance choice is a latent maintainability risk.

**Suggestion:** Consider a separate base class that does not inherit from `FrameworkError`:

```python
class ControlFlowSignal(BaseException):
    """Base for non-error control-flow sentinels (e.g. skip, abort)."""

class SkipElementSignal(ControlFlowSignal):
    ...
```

This is a low-priority refactor; the current code is functionally correct.

---

_Reviewed: 2026-05-26T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
