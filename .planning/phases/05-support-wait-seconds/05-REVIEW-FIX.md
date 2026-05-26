---
phase: 05-support-wait-seconds
fixed_at: 2026-05-25T21:38:00Z
review_path: .planning/phases/05-support-wait-seconds/05-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-05-25T21:38:00Z
**Source review:** .planning/phases/05-support-wait-seconds/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: WAIT_SECONDS does not short-circuit pre-dispatch readiness checks

**Files modified:** `src/waits/wait_manager.py`, `tests/unit/test_wait_manager.py`
**Commit:** a8393fe
**Applied fix:** Added an early-return guard at the top of `wait_for_condition()` that checks `if ctype == WaitConditionType.WAIT_SECONDS:`, calls `self._sleep_seconds(t)`, and returns immediately — bypassing the four readiness pre-checks (document ready, AJAX idle, spinner gone, overlay gone). Added `test_wait_seconds_bypasses_pre_checks_when_require_document_ready_set` to `TestWaitSecondsDispatch` to assert that `wait_for` is never called when `require_document_ready=True` is set alongside `WAIT_SECONDS`.

### WR-02: `_sleep_seconds` type annotation accepts `int` but `time.sleep` safely accepts `float`

**Files modified:** `src/waits/wait_manager.py`
**Commit:** a8393fe
**Applied fix:** Widened `_sleep_seconds` parameter annotation from `seconds: int` to `seconds: float`. Changed the `%d` format specifier in the `logger.warning` call to `%s` so that float values render correctly rather than being silently truncated. Both changes were applied to `wait_manager.py` and landed in the same atomic commit as WR-01 (the two fixes are to the same file and were staged together).

---

_Fixed: 2026-05-25T21:38:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
