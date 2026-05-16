# Phase 3: Support Tab Switching and New Window Focus - Research

**Researched:** 2026-05-15
**Domain:** Selenium window/tab management, action dispatch extension, workflow JSON schema
**Confidence:** HIGH

## Summary

Phase 3 adds the ability for a workflow JSON to declare an action that opens a new browser tab or window and focuses it, with subsequent workflow steps running in that new context. The Selenium API for this is well-established and available in the installed Selenium 4.36.0: `driver.switch_to.new_window("tab")` or `"window"` opens and focuses in one call; `driver.window_handles` lists open handles; `driver.switch_to.window(handle)` switches focus to an existing handle. There are also `EC.new_window_is_opened()` and `EC.number_of_windows_to_be()` expected conditions already in the Selenium stdlib for waiting reliably on new window appearance. [VERIFIED: python introspection of installed selenium 4.36.0]

The framework currently has zero window-switching code — no `window_handle`, `switch_to`, or `new_window` calls exist anywhere in `src/` or `tests/`. [VERIFIED: grep across src/ and tests/ returns no matches] This means the implementation is purely additive: a new `ActionType`, a new `BasePage` method (or a dedicated `WindowManager` helper), dispatch wiring in `ElementActions`, and context propagation in `WorkflowEngine` so that pages/sections executed after the switch run in the new window.

The most significant design decision is **context propagation**: once the driver's focus shifts to a new window, `WorkflowEngine` must not reset focus for subsequent steps. The driver's active window is global state on the `WebDriver` instance — switching once propagates automatically to all later `_driver.find_element()` calls. No new context-tracking data structure is needed; the switch itself is sufficient.

**Primary recommendation:** Add `ActionType.SWITCH_TO_NEW_WINDOW` and `ActionType.SWITCH_TO_NEW_TAB` to enums, add a `BasePage.open_new_window(type_hint)` method and a `BasePage.switch_to_latest_window()` method, wire dispatch in `ElementActions.execute()`, and add unit tests following the established mock-based pattern in `test_action_dispatch.py`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Open a new browser tab/window | UI layer (`BasePage`) | Actions layer (`ElementActions`) | All Selenium driver calls are encapsulated in `BasePage`; the action layer dispatches to it |
| Switch focus to a specific window handle | UI layer (`BasePage`) | — | Same pattern as `check()`/`select_radio()` — thin wrapper over a Selenium primitive |
| Wait for new window to appear | Waits layer (`WaitManager`) | UI layer (`BasePage`) | `EC.new_window_is_opened` is an expected condition; fits the existing `wait_for` pattern |
| Dispatch tab-switch actions | Actions layer (`ElementActions`) | — | Follows `if/elif action == ActionType.X` pattern established in `element_actions.py` |
| Enum schema for new actions | Models layer (`src/core/enums.py`) | — | Pydantic enforces enum membership at JSON load time |
| Context propagation after switch | Driver/WebDriver global state | Workflow layer (`WorkflowEngine`) | `switch_to.window()` updates `driver.current_window_handle`; all subsequent calls use it automatically |
| JSON declaration of tab-switch | Workflow JSON / `ElementDefinition` | Models layer | `ElementDefinition` with the new `ActionType` — no schema change to `TabDefinition` needed |

## Standard Stack

### Core (all already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| selenium | 4.36.0 | Window handle API: `driver.switch_to.new_window()`, `driver.window_handles`, `driver.switch_to.window()` | Framework foundation; all window ops are built-in |
| selenium EC | 4.36.0 | `EC.new_window_is_opened(current_handles)`, `EC.number_of_windows_to_be(n)` | Already used via `WaitManager.wait_for()` |
| pydantic | 2.13.3 | Enum validation for new `ActionType` values | Already used for all models |
| pytest + unittest.mock | existing | Mock-based unit tests | Established pattern in `test_action_dispatch.py` |

### No New Dependencies

Phase 3 requires zero new packages. All Selenium window management primitives are present in the installed version.

**Installation:** None required.

## Architecture Patterns

### System Architecture Diagram

```
Workflow JSON
    │  ElementDefinition(type=BUTTON, action=SWITCH_TO_NEW_WINDOW)
    │  or ElementDefinition(type=BUTTON, action=SWITCH_TO_NEW_TAB)
    ▼
ActionFactory.run(element)
    │  pre_wait (optional) → WaitManager
    ▼
ElementActions.execute(element, value)
    │
    ├── ActionType.SWITCH_TO_NEW_WINDOW
    │       └── BasePage.open_new_window("window")
    │               ├── capture current_handles = driver.window_handles
    │               ├── driver.switch_to.new_window("window")  ← opens AND switches in one call
    │               └── [driver focus is now on new window]
    │
    ├── ActionType.SWITCH_TO_NEW_TAB
    │       └── BasePage.open_new_window("tab")
    │               └── [same flow, type_hint="tab"]
    │
    └── [subsequent elements in same or later sections/pages]
            └── All driver calls use driver.current_window_handle automatically
                (no engine-level change needed)
    │
    post_wait (optional) → WaitManager
         └── EC.number_of_windows_to_be(2) or EC.new_window_is_opened(prev_handles)
```

### Recommended Project Structure

No new directories. All changes fit within existing structure:

```
src/
├── core/
│   └── enums.py                  # Add SWITCH_TO_NEW_WINDOW, SWITCH_TO_NEW_TAB to ActionType
├── ui/
│   └── base_page.py              # Add open_new_window(type_hint) and switch_to_latest_window()
├── actions/
│   └── element_actions.py        # Add dispatch branches for the two new ActionTypes
tests/
├── unit/
│   └── test_action_dispatch.py   # Add unit tests for new dispatch paths
testdata/
└── workflows/
    └── tabs/
        └── new_window_tab.json   # New fixture for unit/smoke tests
```

### Pattern 1: Dispatch by ActionType (existing pattern — follow exactly)

**What:** `ElementActions.execute()` maps `ActionType` values to `BasePage` method calls using `if/elif` branches.
**When to use:** Every new action type follows this exact pattern without exception.
**Example (current code):**
```python
# Source: src/actions/element_actions.py (verified by reading)
elif action == ActionType.SELECT_RADIO:
    self._page.select_radio(element.locator, element.name)
```

New dispatch branches follow the same shape:
```python
elif action == ActionType.SWITCH_TO_NEW_WINDOW:
    self._page.open_new_window("window")

elif action == ActionType.SWITCH_TO_NEW_TAB:
    self._page.open_new_window("tab")
```

### Pattern 2: `switch_to.new_window()` opens AND focuses in one call

**What:** `driver.switch_to.new_window(type_hint)` opens a new browsing context AND switches focus to it atomically. After this call, `driver.current_window_handle` is the new window's handle. [VERIFIED: python introspection of selenium 4.36.0 `SwitchTo.new_window` source]

```python
# Source: selenium/webdriver/remote/switch_to.py (verified by reading via inspect)
def new_window(self, type_hint: Optional[str] = None) -> None:
    value = self._driver.execute(Command.NEW_WINDOW, {"type": type_hint})["value"]
    self._w3c_window(value["handle"])  # <-- also switches to the handle immediately
```

**Implication for BasePage:** `open_new_window(type_hint)` is a 2-line method — call `switch_to.new_window(type_hint)`. No separate switch step is needed for the "open new" case.

### Pattern 3: `switch_to_latest_window()` for when a new window opens via click (not via `new_window`)

**What:** Some workflows trigger a new window by clicking a link (`target="_blank"`) rather than an explicit open command. In that case, the framework must wait for the new window to appear and then switch to it.
**When to use:** When `element.action == ActionType.CLICK` causes a new window to appear and a subsequent element needs to run there. This can be expressed as a `post_wait` with a new `WaitConditionType` or as a separate `switch_to_latest_window` action.
**Recommended approach for Phase 3:** Add `ActionType.SWITCH_TO_LATEST_WINDOW` as a third action type that:
1. Waits for `len(driver.window_handles) > 1` (uses `EC.new_window_is_opened`)
2. Switches to `driver.window_handles[-1]`

This covers the "click opens new window, then explicitly switch to it" pattern that is common in real workflows. [ASSUMED: the phase description mentions "opens/switches to a new browser tab or window" — both open-and-switch and switch-to-existing-window patterns are needed for complete coverage]

### Pattern 4: Context propagation is automatic — no WorkflowEngine change needed

**What:** `driver.switch_to.window(handle)` is a side effect on the global `WebDriver` instance. After it is called, every subsequent `find_element`, `execute_script`, and URL navigation uses the new window automatically.
**Finding:** `WorkflowEngine` holds a single `self._driver` reference. After `BasePage.open_new_window()` runs, the same `self._driver` is now focused on the new window. `DynamicPage.ensure_ready()`, `DynamicSection`, and `ActionFactory` all receive the same `_driver` — no changes to `WorkflowEngine`, `ExecutionContext`, `Navigator`, or `ResultCollector` are required. [VERIFIED: reading WorkflowEngine, BasePage, ActionFactory source — single driver instance flows through entire hierarchy]

**Critical caveat:** If a workflow needs to switch back to the original window, it would require another `SWITCH_TO_LATEST_WINDOW` or a handle-based switch. Phase 3 does not need to support switching back — the success criteria only requires "subsequent actions execute in the new window context." Handle tracking for multi-window round-trips is a future concern.

### Pattern 5: `ElementDefinition.locator` can be made optional for window-switch actions

**What:** `open_new_window` and `switch_to_latest_window` do not target a specific DOM element — they operate on the browser's window context. The current `ElementDefinition` model requires a `locator` field (non-optional). [VERIFIED: reading `src/models/workflow_models.py` — `locator: LocatorDefinition` with no `Optional` wrapper]

**Options:**
- **Option A (recommended):** Use a sentinel locator in JSON, e.g. `"locator": {"by": "id", "value": "_window"}`. The dispatch branch ignores it. Simple, zero model change.
- **Option B:** Make `locator` optional in `ElementDefinition`. Requires model change + validator update + all existing tests that use `_make_element()` assume a locator is present.
- **Option C:** Add a new model `WindowActionDefinition` that lives alongside `ElementDefinition`. Requires changes to `SectionDefinition.elements` type hint and JSON parsing.

**Recommendation:** Option A. Phase 2 established the pattern of making `ElementDefinition` generic — the action dispatch can simply not use the locator for window-switch actions. The `value` field (already `Optional[Any]`) can carry a URL to navigate to in the new window if needed.

### Anti-Patterns to Avoid

- **Do not use `time.sleep()` to wait for the new window to appear.** Use `EC.new_window_is_opened(current_handles)` via `WaitManager.wait_for()`. CLAUDE.md explicitly prohibits sleep-based synchronization.
- **Do not cache `driver.window_handles` without capturing it before the action that opens the window.** The list changes after the new window opens; you must snapshot it before clicking/opening.
- **Do not assume `driver.window_handles[-1]` is always the newest window.** The W3C spec does not guarantee ordering of `window_handles`. Always use `set(new_handles) - set(old_handles)` to find the new handle reliably.
- **Do not modify `TabDefinition` or the workflow JSON hierarchy.** The "tab-switch" in this phase is a browser-level operation triggered by an `ElementDefinition` action, not a structural change to the `Workflow → Tabs → Pages → Sections → Elements` hierarchy. The word "tab" in the phase description refers to browser tabs/windows, not the workflow hierarchy `TabDefinition`.
- **Do not call `switch_to.new_window()` and then `switch_to.window()` separately.** `new_window()` already switches focus; adding a second switch is a no-op at best, a race condition at worst.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detect new window appeared | Custom polling loop | `EC.new_window_is_opened(current_handles)` via `WaitManager.wait_for()` | Already in Selenium EC stdlib; handles race conditions |
| Find the newly opened handle | `driver.window_handles[-1]` (assumes order) | `set(driver.window_handles) - set(old_handles)` → pop one element | W3C spec does not guarantee handle ordering |
| Open + focus new window in one step | Separate open + switch calls | `driver.switch_to.new_window(type_hint)` | Atomically opens AND switches; no race between open and switch |
| Window count wait | Custom while loop | `EC.number_of_windows_to_be(n)` | Already in Selenium EC stdlib; fits `WaitManager.wait_for()` exactly |

**Key insight:** Selenium 4's `switch_to.new_window()` API is specifically designed for this use case and eliminates all the race conditions that plagued Selenium 3's approach of opening a new window and then guessing its handle.

## Common Pitfalls

### Pitfall 1: Assuming handle order in `window_handles`

**What goes wrong:** Code does `new_handle = driver.window_handles[-1]` assuming the newest window is always last. In practice, the W3C WebDriver spec specifies that handle ordering is implementation-defined. Chrome typically appends, but this is not guaranteed.
**Why it happens:** Tutorials and examples frequently use the `[-1]` shortcut.
**How to avoid:** Snapshot handles before the action: `old_handles = set(driver.window_handles)`. After the action and after waiting for the new window: `new_handle = (set(driver.window_handles) - old_handles).pop()`.
**Warning signs:** Tests pass locally (Chrome always appends) but flake in CI or other browsers.

### Pitfall 2: Forgetting to wait before switching

**What goes wrong:** Calling `driver.switch_to.window(handle)` on a handle that does not yet exist raises `NoSuchWindowException`. This happens when the trigger (e.g. a click on `target="_blank"`) is asynchronous.
**Why it happens:** The window open event is not synchronous with the Selenium click command returning.
**How to avoid:** For `SWITCH_TO_LATEST_WINDOW`, always run `EC.new_window_is_opened(old_handles)` before computing the new handle and switching. `WaitManager.wait_for()` with a reasonable timeout (10s default) is sufficient.
**Warning signs:** `NoSuchWindowException` in the dispatch; intermittent failures on slow CI.

### Pitfall 3: Confusing workflow `TabDefinition` with browser tabs

**What goes wrong:** Developer adds a new field to `TabDefinition` (e.g. `open_new_window: bool`) thinking the workflow hierarchy "Tab" maps to a browser tab. It does not — `TabDefinition` is a workflow grouping abstraction, not a browser concept.
**Why it happens:** The naming collision between "workflow tab" and "browser tab" is the most common source of confusion in this phase.
**How to avoid:** The tab-switch is an `ElementDefinition` action within the existing hierarchy. No changes to `TabDefinition`, `PageDefinition`, or `WorkflowEngine`'s traversal logic are needed.
**Warning signs:** Any edit to `workflow_models.py` beyond adding to `ActionType` in `enums.py`.

### Pitfall 4: Making `locator` optional in `ElementDefinition` for this phase

**What goes wrong:** Making `locator` optional in `ElementDefinition` requires updating validators, all `_make_element()` usages in tests, and the JSON schema. This is a wide blast radius for what is a cosmetic concern.
**Why it happens:** Window-switch actions don't need a locator, so it feels wrong to require one.
**How to avoid:** Use Option A — a sentinel locator value in JSON (e.g. `{"by": "id", "value": "_window"}`). The dispatch branch ignores it. Keep `locator` required in the model.
**Warning signs:** Any modification to `ElementDefinition` other than adding new enum values.

### Pitfall 5: Using `driver.execute_script("window.focus()")` for Chrome focus

**What goes wrong:** `window.focus()` via JS does not reliably bring a Chrome window to the OS foreground (especially in headless mode or when the window is minimized). It affects JavaScript focus within the current browsing context, not the OS window manager.
**Why it happens:** Searching for "selenium focus window" returns JS-based approaches.
**How to avoid:** Use `driver.switch_to.window(handle)` — this is the correct W3C mechanism. For OS-level foreground focus in headed mode, `driver.maximize_window()` after the switch can help but is not required for the browser to execute actions correctly.
**Warning signs:** Adding `execute_script("window.focus()")` or `execute_script("window.blur()")` in the implementation.

## Code Examples

Verified patterns from Selenium source and existing codebase:

### Open new browser window (new_window API — atomic open + switch)
```python
# Source: selenium/webdriver/remote/switch_to.py (verified by inspect in this session)
# In BasePage:
def open_new_window(self, type_hint: str = "window") -> None:
    """Open a new browser window or tab and switch focus to it.

    Args:
        type_hint: 'window' for a new OS window, 'tab' for a new tab.
    """
    self._driver.switch_to.new_window(type_hint)
```

### Switch to the latest newly-opened window (for click-triggered new windows)
```python
# Source: derived from EC.new_window_is_opened (verified by inspect in this session)
# In BasePage:
def switch_to_latest_window(self, timeout: int = 10) -> None:
    """Wait for a new window to appear and switch focus to it.

    Use this after an action (e.g. clicking a link) that opens a new window
    asynchronously. Captures handles before calling, waits for count to grow,
    then switches to the new handle.
    """
    from selenium.webdriver.support import expected_conditions as EC

    old_handles = set(self._driver.window_handles)
    self._wm.wait_for(
        EC.new_window_is_opened(list(old_handles)),
        "new window to appear",
        timeout=timeout,
    )
    new_handles = set(self._driver.window_handles) - old_handles
    new_handle = new_handles.pop()
    self._driver.switch_to.window(new_handle)
```

### Existing check() pattern (canonical model for new BasePage methods)
```python
# Source: src/ui/base_page.py (verified by reading)
def check(self, locator: LocatorDefinition, name: str = "") -> None:
    """Check a checkbox if not already checked."""
    el = self.wait_for_visible(locator)
    if not el.is_selected():
        el.click()
```

### Dispatch in ElementActions (pattern to follow)
```python
# Source: src/actions/element_actions.py (verified by reading)
elif action == ActionType.SELECT_RADIO:
    self._page.select_radio(element.locator, element.name)

# New branches follow the same shape:
elif action == ActionType.SWITCH_TO_NEW_WINDOW:
    self._page.open_new_window("window")

elif action == ActionType.SWITCH_TO_NEW_TAB:
    self._page.open_new_window("tab")

elif action == ActionType.SWITCH_TO_LATEST_WINDOW:
    self._page.switch_to_latest_window()
```

### Workflow JSON declaration
```json
{
  "name": "Open New Window",
  "type": "button",
  "action": "switch_to_new_window",
  "locator": { "by": "id", "value": "_window" }
}
```
```json
{
  "name": "Switch to Latest Window",
  "type": "button",
  "action": "switch_to_latest_window",
  "locator": { "by": "id", "value": "_window" }
}
```

### Unit test pattern (mock-based, no browser — canonical from test_action_dispatch.py)
```python
# Source: tests/unit/test_action_dispatch.py (verified by reading)
def test_check_action(self, executor, mock_page):
    el = _make_element(etype=ElementType.CHECKBOX, action=ActionType.CHECK)
    executor.execute(el)
    mock_page.check.assert_called_once_with(el.locator, el.name)
```

New test for window-switch dispatch:
```python
def test_switch_to_new_window_action(self, executor, mock_page):
    el = _make_element(etype=ElementType.BUTTON, action=ActionType.SWITCH_TO_NEW_WINDOW)
    executor.execute(el)
    mock_page.open_new_window.assert_called_once_with("window")

def test_switch_to_new_tab_action(self, executor, mock_page):
    el = _make_element(etype=ElementType.BUTTON, action=ActionType.SWITCH_TO_NEW_TAB)
    executor.execute(el)
    mock_page.open_new_window.assert_called_once_with("tab")

def test_switch_to_latest_window_action(self, executor, mock_page):
    el = _make_element(etype=ElementType.BUTTON, action=ActionType.SWITCH_TO_LATEST_WINDOW)
    executor.execute(el)
    mock_page.switch_to_latest_window.assert_called_once()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Selenium 3: `driver.execute_script("window.open()")` + manual handle detection | Selenium 4: `driver.switch_to.new_window(type_hint)` opens AND switches atomically | Selenium 4.0 (2021) | No more manual handle guessing for the "open new window" case |
| Poll `window_handles` with `time.sleep` | `EC.new_window_is_opened(old_handles)` via `WebDriverWait` | Selenium 4.x | Fits `WaitManager.wait_for()` pattern without sleep |

**Deprecated/outdated:**
- `driver.execute_script("window.open('')")`: Selenium 3 pattern — produces a blank window and requires manual handle detection. Use `driver.switch_to.new_window("window")` instead.
- Assuming `driver.window_handles[-1]` is the new handle: still works in Chrome but is not spec-compliant.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `SWITCH_TO_LATEST_WINDOW` as a third distinct action type is needed to cover click-triggered new windows | Pattern 3 | If the phase scope is strictly "open new window only" (not click-triggered), this action type can be omitted — but it's low-cost to add and makes the framework more complete |
| A2 | A sentinel locator value (Option A) is acceptable for window-switch actions that don't target a DOM element | Pattern 5 | If the project decides `locator` should be optional for non-element actions, a model change is needed — but this is a user preference question, not a technical one |

**All other claims in this document were verified by reading source files or via Python introspection of the installed Selenium 4.36.0 in this session.**

## Open Questions

1. **Should `SWITCH_TO_LATEST_WINDOW` be a separate action type?**
   - What we know: Two patterns exist — (a) explicit open-and-switch via `switch_to.new_window()`, (b) click-triggered asynchronous window open needing a post-click switch. Phase 3 success criteria says "opens/switches to a new browser tab or window."
   - What's unclear: Whether the user expects (a) only, or also (b).
   - Recommendation: Include all three action types (`SWITCH_TO_NEW_WINDOW`, `SWITCH_TO_NEW_TAB`, `SWITCH_TO_LATEST_WINDOW`). Low cost, covers both patterns, makes the framework complete for real-world use.

2. **Should `locator` be made optional in `ElementDefinition`?**
   - What we know: Window-switch actions don't need a locator. Requiring a sentinel value in JSON is awkward but zero-cost in code.
   - What's unclear: User preference on JSON ergonomics vs. model complexity.
   - Recommendation: Keep `locator` required (Option A — sentinel value). Defer making it optional to a future phase if the ergonomics matter.

3. **Should the new window's URL be navigated to automatically?**
   - What we know: `switch_to.new_window()` opens `about:blank`. Subsequent page steps with a `path` field would navigate via `Navigator.navigate_to_page()`, which already handles this.
   - What's unclear: Whether Phase 3 needs to pass a URL as part of the window-open action or whether relying on the existing `PageDefinition.path` navigation is sufficient.
   - Recommendation: Rely on existing `PageDefinition.path` navigation. The `value` field in `ElementDefinition` (already `Optional[Any]`) can carry a URL if explicit navigation on open is desired, but this is not required for success criteria.

## Environment Availability

Step 2.6: SKIPPED — Phase 3 is code/config changes only. No external services, databases, or CLI tools beyond the existing Python/pytest/Selenium stack, all already confirmed installed and operational (130 unit tests pass at baseline).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 [VERIFIED: unit test run — 130 passed] |
| Config file | `pytest.ini` (rootdir) |
| Quick run command | `pytest tests/unit/test_action_dispatch.py -v` |
| Full suite command | `pytest tests/unit/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SC-1 | `ActionType.SWITCH_TO_NEW_WINDOW` accepted by Pydantic | unit | `pytest tests/unit/test_workflow_models.py -x` | Extend existing |
| SC-1 | `ActionType.SWITCH_TO_NEW_TAB` accepted by Pydantic | unit | `pytest tests/unit/test_workflow_models.py -x` | Extend existing |
| SC-1 | `SWITCH_TO_NEW_WINDOW` dispatches to `BasePage.open_new_window("window")` | unit | `pytest tests/unit/test_action_dispatch.py::TestElementActions::test_switch_to_new_window_action -x` | Wave 0 gap |
| SC-1 | `SWITCH_TO_NEW_TAB` dispatches to `BasePage.open_new_window("tab")` | unit | `pytest tests/unit/test_action_dispatch.py::TestElementActions::test_switch_to_new_tab_action -x` | Wave 0 gap |
| SC-2 | `SWITCH_TO_LATEST_WINDOW` dispatches to `BasePage.switch_to_latest_window()` | unit | `pytest tests/unit/test_action_dispatch.py::TestElementActions::test_switch_to_latest_window_action -x` | Wave 0 gap |
| SC-3 | Subsequent element actions use `_driver` in new window context (driver state propagation) | unit | Covered by SC-2 test — driver state is global; no separate test needed | N/A |
| SC-4 | `BasePage.open_new_window()` calls `driver.switch_to.new_window(type_hint)` | unit | `pytest tests/unit/test_base_page_window.py -x` | Wave 0 gap (new file) |
| SC-4 | `BasePage.switch_to_latest_window()` waits for new window then switches | unit | `pytest tests/unit/test_base_page_window.py -x` | Wave 0 gap (new file) |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/test_action_dispatch.py -v`
- **Per wave merge:** `pytest tests/unit/ -v`
- **Phase gate:** Full unit suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_action_dispatch.py` — add `test_switch_to_new_window_action`, `test_switch_to_new_tab_action`, `test_switch_to_latest_window_action`
- [ ] `tests/unit/test_base_page_window.py` — new file covering `BasePage.open_new_window()` and `BasePage.switch_to_latest_window()` with mocked driver

*(No new framework config or conftest changes needed — infrastructure fully exists)*

## Security Domain

No security-sensitive concerns for this phase. The changes are:
- Enum value additions in `enums.py` (no user input, no auth)
- Window management dispatch routing (operates within the same browser session; no cross-origin access)
- Unit test additions (mock-based, no network)

ASVS V5 (Input Validation): The `type_hint` value passed to `driver.switch_to.new_window()` is an enum-controlled string ("window" or "tab") — not user-supplied input. Pydantic enum validation guards the entry point.

## Sources

### Primary (HIGH confidence)

- `src/core/enums.py` — verified all current `ElementType` and `ActionType` values; `SWITCH_TO_NEW_WINDOW` etc. do not yet exist [VERIFIED: reading file in this session]
- `src/actions/element_actions.py` — verified complete dispatch table; no window-switch branches [VERIFIED: reading file in this session]
- `src/ui/base_page.py` — verified all existing methods; no `switch_to` or `window_handles` usage [VERIFIED: reading file in this session]
- `src/workflow/workflow_engine.py` — verified single `_driver` instance flows through entire hierarchy; no context-tracking changes needed [VERIFIED: reading file in this session]
- `src/models/workflow_models.py` — verified `ElementDefinition.locator` is required (non-optional) [VERIFIED: reading file in this session]
- `selenium==4.36.0` — `SwitchTo.new_window()`, `SwitchTo.window()`, `WebDriver.window_handles`, `EC.new_window_is_opened`, `EC.number_of_windows_to_be` all verified via Python introspection [VERIFIED: `python3 -c "import inspect; from selenium..."` in this session]
- `pytest tests/unit/ -v` run — 130 tests pass; baseline confirmed [VERIFIED: run in this session]
- grep across `src/` and `tests/` for `window_handle|switch_to|new_window` — zero matches; no existing window code [VERIFIED: bash grep in this session]

### Secondary (MEDIUM confidence)

- None required — all claims verified against installed source.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified against installed selenium 4.36.0 via Python introspection
- Architecture: HIGH — complete codebase read, all relevant source files verified
- Pitfalls: HIGH — derived from Selenium spec knowledge and reading actual installed source
- Test gaps: HIGH — derived from diffing existing tests against phase success criteria

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (stable codebase; selenium 4.x window API is mature and stable)
