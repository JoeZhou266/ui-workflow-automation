# Phase 6: Support execute_js_script Action Type - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Add an `EXECUTE_JS_SCRIPT` action type so workflow JSON can execute arbitrary
JavaScript in the browser. The JavaScript string is read from `element.value`
and dispatched via `driver.execute_script(value)`. No DOM element targeting
is performed — this is a pure script execution action.

</domain>

<decisions>
## Implementation Decisions

### ElementType
- **D-01:** Add `SCRIPT = "script"` to `ElementType` in `src/core/enums.py`.
  JSON authors write `"type": "script"` when declaring an execute_js_script element.
  This makes intent explicit and avoids semantic confusion (avoids reusing `BUTTON`
  the way window-switch actions do).

### ActionType
- **D-02:** Add `EXECUTE_JS_SCRIPT = "execute_js_script"` to `ActionType` in
  `src/core/enums.py`. JSON authors write `"action": "execute_js_script"`.

### Dispatch implementation
- **D-03:** Add a branch in `ElementActions.execute()` that calls
  `self._page._driver.execute_script(str(value))` (or equivalent). No element
  is resolved or passed as an argument — pure script, value-only.

### Claude's Discretion
- **Locator field:** `ElementDefinition.locator` remains required (no model change).
  JSON authors supply a dummy locator (e.g. `{"by": "id", "value": "n/a"}`) when
  using this action — consistent with how window-switch actions handle it today.
- **Return value:** The return value of `execute_script()` is silently ignored —
  no logging, no storage. Consistent with other void-style actions (CLICK, CHECK).
- **Element binding:** No element is passed as `arguments[0]` — value-only execution.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core framework files (read before planning)
- `src/core/enums.py` — `ElementType` and `ActionType` enums; add new values here
- `src/actions/element_actions.py` — `ElementActions.execute()` dispatch chain; add branch here
- `src/models/workflow_models.py` — `ElementDefinition`; `value: Optional[Any]` carries the JS string
- `CLAUDE.md` §Architecture — layer responsibilities and key constraints

### Existing tests to understand before writing new ones
- `tests/unit/test_action_dispatch.py` — pattern for dispatch unit tests
- `tests/unit/test_workflow_models.py` — pattern for model validation tests (enum membership)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ElementActions.execute()` if/elif chain (`src/actions/element_actions.py:46`) — new branch goes here, after `SWITCH_TO_LATEST_WINDOW`
- `BasePage._driver` — `execute_script()` is available via `self._page._driver` (or expose a helper on `BasePage`)
- `_make_element()` / `_make_locator()` in `tests/unit/test_action_dispatch.py` — test helpers that build `ElementDefinition` with a dummy locator

### Established Patterns
- Every new `ActionType` value gets an `elif` branch in `ElementActions.execute()`
- Window-switch actions (Phase 3) set the pattern for locator-unused actions: keep locator required, supply dummy in JSON/tests
- `ElementType.BUTTON` was reused for window-switch; Phase 6 breaks this by adding a dedicated `SCRIPT` type — cleaner going forward
- All action errors are wrapped in `ElementActionError`

### Integration Points
- `ActionFactory.run()` → `ElementActions.execute()` → new branch
- `BasePage._driver` is already accessible from `ElementActions` via `self._page._driver`
- No changes needed to `WaitManager`, `WorkflowRunner`, or any model beyond the two enum additions

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond D-01 through D-03 — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-support-execute-js-script*
*Context gathered: 2026-05-25*
