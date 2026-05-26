---
phase: 07-support-skip-if-not-visible
plan: "01"
subsystem: actions
tags: [selenium, skip, visibility, conditional-execution, exceptions, tdd]

requires:
  - phase: 06-support-execute-js-script
    provides: BasePage.execute_script, ElementType.SCRIPT, ActionType.EXECUTE_JS_SCRIPT

provides:
  - SkipElementSignal exception class in src/core/exceptions.py
  - Visibility probe guard in ActionFactory.run() using self._page.is_visible()
  - except SkipElementSignal branch in WorkflowEngine._run_element() calling record_skip()
  - 4 new unit tests covering the full skip_if_not_visible contract

affects:
  - Any future phase adding conditional element execution or workflow branching

tech-stack:
  added: []
  patterns: [control-flow-via-exception, tdd-red-green]

key-files:
  created: []
  modified:
    - src/core/exceptions.py
    - src/actions/action_factory.py
    - src/workflow/workflow_engine.py
    - tests/unit/test_action_dispatch.py
    - tests/unit/test_result_collector.py

key-decisions:
  - "SkipElementSignal inherits FrameworkError (not BaseException) — keeps it in the typed exception hierarchy alongside ElementActionError"
  - "Visibility probe runs before resolved_value = _resolver.resolve(...) — guarantees pre_wait is never called for skipped elements"
  - "No screenshot on skip — SkipElementSignal is an expected control-flow event, not an error"

patterns-established:
  - "Control-flow signal pattern: use a typed FrameworkError subclass (not a boolean return) to exit factory.run() early — keeps callers decoupled from internal state"
  - "Options dict access: element.options and element.options.get('key') — safe against None options"

requirements-completed:
  - "SC-01: SkipElementSignal exception class exists in src/core/exceptions.py"
  - "SC-02: ActionFactory.run() stores self._page and raises SkipElementSignal before pre_wait when element.options.skip_if_not_visible=True and element is not visible"
  - "SC-03: WorkflowEngine._run_element() catches SkipElementSignal and calls self._collector.record_skip() with reason='skip_if_not_visible=true'"
  - "SC-04: Visibility probe runs BEFORE pre_wait — pre_wait is never called for skipped elements"
  - "SC-05: Unit tests cover: signal raised when not visible, no signal when visible, pre_wait not called, record_skip increments skipped count"

duration: 15min
completed: 2026-05-26
---

# Phase 07: support-skip-if-not-visible Summary

**`skip_if_not_visible` conditional execution via SkipElementSignal exception — visibility probe before pre_wait, skipped steps recorded as SKIPPED not FAILED**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-26T09:40:00Z
- **Completed:** 2026-05-26T09:55:00Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 5

## Accomplishments

- Added `SkipElementSignal(FrameworkError)` to `src/core/exceptions.py` — control-flow signal for invisible optional elements
- Added visibility probe guard in `ActionFactory.run()` using `self._page.is_visible()` before `_resolver.resolve()` — guarantees pre_wait is never invoked for skipped elements
- Added `except SkipElementSignal` branch in `WorkflowEngine._run_element()` calling `record_skip(..., reason="skip_if_not_visible=true")` — no screenshot, no FAILED status
- 4 new passing unit tests covering all 5 requirements (SC-01 through SC-05)

## Task Commits

1. **Task 1 (RED): Write failing tests** - `14d1e43` (test)
2. **Task 2 (GREEN): Implementation** - `2faecdf` (feat)

## Files Created/Modified

- `src/core/exceptions.py` — Appended `SkipElementSignal` after `WorkflowExecutionError`
- `src/actions/action_factory.py` — Added `self._page`, updated import, added visibility probe guard
- `src/workflow/workflow_engine.py` — Updated import, added `except SkipElementSignal` branch
- `tests/unit/test_action_dispatch.py` — 3 new `TestActionFactory` tests
- `tests/unit/test_result_collector.py` — 1 new `TestResultCollector` test

## Decisions Made

- Used control-flow-via-exception pattern (SkipElementSignal) rather than returning a boolean from `factory.run()` — keeps `_run_element` decoupled, consistent with `ElementActionError` pattern already in place
- Probe placed before `_resolver.resolve(element.value)` (not before pre_wait) — simpler and matches requirement SC-04 exactly
- No screenshot on SkipElementSignal — skip is expected behavior, not an error

## Deviations from Plan

None — plan executed exactly as written. All 5 requirements verified by unit tests.

## Issues Encountered

None. The pre-existing `test_value_resolver.py` failures (5 tests in `TestGenerators`/`TestPlaceholderRegistry` related to `generate_sin_number()`) are unrelated to phase 07 and were present before any changes.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Phase 07 is the final phase of milestone v1.0. All 7 phases complete.

- `skip_if_not_visible: true` option in workflow JSON now causes optional elements to be recorded as SKIPPED when not visible, enabling conditional UI workflows without false failures
- Framework is ready for: additional `options` fields following the same pattern, integration tests with real browser, milestone completion

---
*Phase: 07-support-skip-if-not-visible*
*Completed: 2026-05-26*
