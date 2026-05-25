# Phase 5: Support wait_seconds in WaitConditionType - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `wait_seconds` condition to `WaitConditionType` so workflow JSON can declare a
fixed-duration pause in `pre_wait` / `post_wait`. No locator or element condition is
required — the pause runs unconditionally for the configured number of seconds.

This is the only mechanism for intentional fixed-delay waits in the framework. All
other wait conditions are event-driven (element state, DOM readiness, AJAX idle, etc.).

</domain>

<decisions>
## Implementation Decisions

### Parameter field
- **D-01:** Reuse the existing `timeout` field on `WaitConditionDefinition` to specify
  the sleep duration in seconds. For `wait_seconds`, `timeout` means "sleep exactly
  this many seconds" rather than its usual meaning of "failure deadline."
  No schema change is needed to `WaitConditionDefinition`.

  Example JSON:
  ```json
  "pre_wait": {
    "condition": "wait_seconds",
    "timeout": 2
  }
  ```

### Enum value
- **D-02:** Add `WAIT_SECONDS = "wait_seconds"` to `WaitConditionType` in `src/core/enums.py`.

### Implementation approach
- **D-03:** Implement the sleep in `WaitManager._dispatch()` using `time.sleep(timeout)`.
  Per CLAUDE.md, the sleep must be isolated in a dedicated helper, logged at WARNING,
  and commented with the reason (this IS the feature — intentional fixed-delay pause).

### Claude's Discretion
- Validation strictness: whether to warn/error when irrelevant fields (locator,
  text_expected, attribute_name, etc.) are also set alongside `wait_seconds` — Claude
  decides (silent ignore is fine; a debug-level log is acceptable).
- Integer seconds only (matching the existing `timeout: int` field type — no float
  precision is needed since `timeout` has always been `int`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core framework files (read before planning)
- `src/core/enums.py` — WaitConditionType enum; add WAIT_SECONDS here
- `src/models/workflow_models.py` — WaitConditionDefinition model; `timeout` field reused
- `src/waits/wait_manager.py` — `_dispatch()` method; add WAIT_SECONDS branch here
- `src/actions/action_factory.py` — pre_wait/post_wait call sites; no changes needed
- `CLAUDE.md` §Synchronization layer — sleep rules: isolated helper, WARNING log, comment

### Existing tests to understand before writing new ones
- `tests/unit/test_action_dispatch.py` — pattern for dispatch unit tests
- `tests/unit/test_workflow_models.py` — pattern for model validation tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `WaitManager.wait_for()` — existing generic wait entry point; NOT used for wait_seconds (sleep bypasses polling)
- `WaitManager._dispatch()` — the if/elif chain where WAIT_SECONDS branch goes; already handles 18 condition types
- `WaitConditionDefinition.timeout` — already validated as `int`, `ge=1`, `le=300`; `wait_seconds` reuses this range

### Established Patterns
- Every `WaitConditionType` maps to exactly one `elif` branch in `_dispatch()` — follow this pattern
- Sleep fallbacks in CLAUDE.md must be "isolated in one helper, configurable, logged at WARNING, and commented with the reason" — a `_sleep_seconds()` private helper on `WaitManager` satisfies this
- Unit tests for dispatch follow the pattern in `test_action_dispatch.py`: mock the page/driver, build an `ElementDefinition`, call `ActionFactory.run()`, assert side effects

### Integration Points
- `ActionFactory.run()` (line ~30) calls `self._wm.wait_for_condition(element.pre_wait)` and `wait_for_condition(element.post_wait)` — these are the call sites; no changes needed here
- `WaitManager.wait_for_condition()` delegates to `_dispatch()` — only `_dispatch()` needs the new branch

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard approach is to add the enum value, add the `_dispatch` branch,
and add a `_sleep_seconds()` helper that wraps `time.sleep` with a WARNING log.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-support-wait-seconds*
*Context gathered: 2026-05-25*
