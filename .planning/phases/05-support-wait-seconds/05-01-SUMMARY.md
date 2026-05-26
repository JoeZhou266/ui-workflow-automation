---
phase: 05-support-wait-seconds
plan: "01"
subsystem: waits
tags:
  - tdd
  - wait-condition
  - enum
  - sleep
dependency_graph:
  requires:
    - src/core/enums.py (WaitConditionType enum)
    - src/waits/wait_manager.py (_dispatch loop)
    - src/models/workflow_models.py (WaitConditionDefinition.timeout field)
  provides:
    - WaitConditionType.WAIT_SECONDS enum value
    - WaitManager._sleep_seconds() helper
    - WAIT_SECONDS dispatch branch in WaitManager._dispatch()
    - TestWaitConditionDefinition (5 model tests)
    - TestWaitSecondsDispatch (7 dispatch tests)
  affects:
    - Any workflow JSON using condition: "wait_seconds" in pre_wait / post_wait
tech_stack:
  added:
    - "import time (stdlib) in wait_manager.py"
  patterns:
    - TDD RED/GREEN cycle
    - Isolated sleep helper per CLAUDE.md synchronization layer rules
    - WARNING-level log for intentional fixed-delay pause
    - Enum extension: append new value to WaitConditionType
    - elif dispatch branch in WaitManager._dispatch()
key_files:
  created:
    - tests/unit/test_wait_manager.py
  modified:
    - src/core/enums.py
    - src/waits/wait_manager.py
    - tests/unit/test_workflow_models.py
decisions:
  - "D-01: Reused existing WaitConditionDefinition.timeout field as sleep duration for WAIT_SECONDS — no schema change needed"
  - "D-02: Added WAIT_SECONDS = 'wait_seconds' as the last value in WaitConditionType enum"
  - "D-03: Implemented sleep via isolated _sleep_seconds() helper on WaitManager with WARNING log and code comment per CLAUDE.md"
metrics:
  duration: "3 minutes"
  completed_date: "2026-05-26"
  tasks_completed: 2
  files_changed: 4
---

# Phase 05 Plan 01: Support wait_seconds in WaitConditionType Summary

**One-liner:** Fixed-duration wait via `WaitConditionType.WAIT_SECONDS` dispatching to an isolated `_sleep_seconds()` helper that logs at WARNING and calls `time.sleep(timeout)`.

## What Was Built

Added a sanctioned fixed-delay pause mechanism to the framework. Workflow JSON can now declare `{"condition": "wait_seconds", "timeout": N}` in any `pre_wait` or `post_wait` block to pause execution for N seconds unconditionally. This is the only mechanism for intentional fixed-delay waits — all other wait conditions are event-driven.

Implementation is minimal (one enum value, one helper method, one elif branch) with full compliance to CLAUDE.md's synchronization layer rules: the sleep is isolated in a dedicated helper, logged at WARNING, and commented with the reason.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Write failing tests for WaitConditionDefinition model and WaitManager dispatch | 2d8a42c | tests/unit/test_workflow_models.py, tests/unit/test_wait_manager.py |
| 2 (GREEN) | Add WAIT_SECONDS enum + _sleep_seconds helper + dispatch branch | de84800 | src/core/enums.py, src/waits/wait_manager.py |

## TDD Gate Compliance

- RED gate commit: `2d8a42c` — `test(05-01): RED — add WaitConditionDefinition + WaitManager dispatch tests for WAIT_SECONDS`
- GREEN gate commit: `de84800` — `feat(05-01): GREEN — implement WAIT_SECONDS via _sleep_seconds helper (per D-01, D-02, D-03)`

Both gates present. RED commit confirmed all 12 tests failing with `AttributeError: WAIT_SECONDS`. GREEN commit confirmed all 12 tests passing.

## Verification Results

All plan verification checks passed:

- `pytest tests/unit/test_workflow_models.py::TestWaitConditionDefinition -v` — 5/5 passed
- `pytest tests/unit/test_wait_manager.py -v` — 7/7 passed
- `pytest tests/unit/ -v` — 176 passed, 5 pre-existing failures in `test_value_resolver.py` (SIN generation, unrelated to this plan)
- `WaitConditionType.WAIT_SECONDS.value == "wait_seconds"` — confirmed
- `WaitManager._sleep_seconds` is callable — confirmed
- `_sleep_seconds` has comment, `logger.warning(` call, and `time.sleep(` call — confirmed
- dispatch branch `elif ctype == WaitConditionType.WAIT_SECONDS` routes to `self._sleep_seconds(timeout)` — confirmed

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all new functionality is fully wired. `WaitConditionType.WAIT_SECONDS` parses from JSON → Pydantic model → `wait_for_condition()` → `_dispatch()` → `_sleep_seconds()` → `time.sleep()`.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. The `time.sleep()` call is pure blocking with no privilege implications. The `timeout` value flowing into `time.sleep()` is bounded by existing Pydantic constraints (`ge=1, le=300`) as documented in the plan's threat model (T-05-01, T-05-02).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/core/enums.py | FOUND |
| src/waits/wait_manager.py | FOUND |
| tests/unit/test_workflow_models.py | FOUND |
| tests/unit/test_wait_manager.py | FOUND |
| .planning/phases/05-support-wait-seconds/05-01-SUMMARY.md | FOUND |
| Commit 2d8a42c (RED) | FOUND |
| Commit de84800 (GREEN) | FOUND |
