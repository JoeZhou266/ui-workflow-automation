# Phase 7: Support skip-if-not-visible - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Add conditional execution to element actions: when `options.skip_if_not_visible` is `true`, the engine checks
whether the element is visible at dispatch time. If visible, the action runs normally. If not visible, the
step is recorded as `SKIPPED` (not `FAILED`) and execution continues to the next element.

No new element types. No changes to the wait layer. No changes to the JSON schema beyond reading a flag
already supported by the existing `options: Dict[str, Any]` field.

</domain>

<decisions>
## Implementation Decisions

### Option Placement
- **D-01:** `skip_if_not_visible` lives in the existing `options` dict on `ElementDefinition`, not as a new top-level field.
  - Key name: `"skip_if_not_visible"` (exact string)
  - Read via `element.options and element.options.get("skip_if_not_visible")`
  - Consistent with the `trigger_change_event` precedent from Phase 2
  - No Pydantic model change required

### Claude's Discretion

The following areas were not discussed by the user — Claude has full discretion:

- **Visibility probe timeout:** Use zero seconds (instant DOM check, no blocking). If the element is not
  present/visible at the moment of dispatch, skip immediately. Do not add wait time for this probe.

- **Skip signal mechanism:** Add a new `SkipElementSignal` exception in `src/core/exceptions.py`.
  `ActionFactory.run()` raises it when the probe finds the element not visible. `WorkflowEngine._run_element()`
  catches it with a dedicated `except SkipElementSignal` branch and calls `self._collector.record_skip()`.
  This mirrors the existing exception-based error handling pattern (WaitTimeoutError, ElementActionError)
  and keeps `ActionFactory.run()` return type as `None`.

- **pre_wait interaction:** The visibility probe runs BEFORE `pre_wait`. If the element is not visible,
  skip immediately without evaluating `pre_wait`. This avoids a pointless wait cost when the intent is
  "don't even try if not there".

- **ResultCollector.record_skip():** Verify it exists; if not, add it. StepStatus.SKIPPED already exists
  in enums — the method just needs to construct a StepResult with that status and no screenshot.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core implementation files
- `src/core/exceptions.py` — Add `SkipElementSignal` here, alongside `ElementActionError`
- `src/core/enums.py` — `StepStatus.SKIPPED` already exists; `ActionType`, `ElementType` unchanged
- `src/actions/action_factory.py` — Add visibility probe guard at top of `run()` before pre_wait
- `src/workflow/workflow_engine.py` — Add `except SkipElementSignal` branch in `_run_element()`
- `src/models/workflow_models.py` — `ElementDefinition.options` field already exists; no change needed

### Precedents to follow
- `src/actions/element_actions.py` line with `element.options.get("trigger_change_event")` — exact pattern for reading from options dict
- `src/workflow/workflow_engine.py` `_run_element()` — existing exception dispatch pattern to mirror
- Phase 5 (`05-support-wait-seconds`) — example of minimal, targeted feature addition with no schema change

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `WaitManager.wait_visible(locator_tuple, timeout)` — pass `timeout=0` for instant probe (raises `WaitTimeoutError` on miss, which becomes the signal to skip)
- `StepStatus.SKIPPED` — already in `src/core/enums.py`
- `ElementDefinition.options: Optional[Dict[str, Any]]` — already on the model, already read in element_actions.py

### Established Patterns
- Exception-based flow control: `WaitTimeoutError` and `ElementActionError` are both caught in `_run_element()` — `SkipElementSignal` slots in as a third branch
- `options.get(key)` for per-element flags: used for `trigger_change_event` — same pattern for `skip_if_not_visible`
- Phase-scoped comments (e.g., `# Phase 6: execute_js_script action type`) — follow this style in new code

### Integration Points
- `ActionFactory.run()` → `WorkflowEngine._run_element()`: the only call site; one method to change in each file
- `ResultCollector` — check for `record_skip()` method; likely needs adding

</code_context>

<specifics>
## Specific Ideas

- From prior conversation: the guard in `ActionFactory.run()` should be:
  ```python
  if element.options and element.options.get("skip_if_not_visible"):
      locator_tuple = LocatorResolver.resolve(element.locator)
      try:
          self._wm.wait_visible(locator_tuple, timeout=0)
      except WaitTimeoutError:
          logger.info("[%s] Not visible — skipping (skip_if_not_visible=true)", element.name)
          raise SkipElementSignal(element.name)
  ```
- JSON usage example (from prior conversation):
  ```json
  {
    "name": "Optional Banner",
    "type": "button",
    "action": "click",
    "locator": { "by": "id", "value": "dismiss-banner" },
    "options": { "skip_if_not_visible": true }
  }
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-support-skip-if-not-visible*
*Context gathered: 2026-05-26*
