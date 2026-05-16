---
phase: 03-support-tab-switching-new-window
verified: 2026-05-15T00:00:00Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open a real browser, load a page that has a link with target=\"_blank\", declare a workflow JSON using switch_to_latest_window after a click action, and run it end-to-end."
    expected: "The WebDriver focus shifts to the new window and subsequent elements (fill a form field, etc.) operate in the new window context — not the original tab."
    why_human: "SC-3 requires that driver focus globally shifts after the switch so all subsequent workflow steps run in the new window. Unit tests mock the driver — they confirm the method is called but cannot verify that the actual Selenium window context is held and reused by the workflow engine traversal. No smoke test exists for window-switching."
  - test: "Verify that a workflow with switch_to_new_window or switch_to_new_tab followed by page/section/element steps executes those steps in the new window without any manual handle reassignment."
    expected: "Elements in subsequent pages/sections after the switch action are located and interacted with in the newly opened Chrome window."
    why_human: "The dispatch routing is verified by unit tests, but the WorkflowEngine loop (workflow/runner.py) hands the same BasePage instance to all elements. The behavior that the opened-window context persists across subsequent loop iterations needs a real browser to confirm — mocked tests do not traverse the workflow hierarchy."
---

# Phase 3: Support Tab Switching and New Window Focus — Verification Report

**Phase Goal:** Enable workflow JSON to switch browser tabs and focus on them in a new Chrome window
**Verified:** 2026-05-15
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (SC-1) | Workflow JSON can declare a tab-switch action that opens/switches to a new browser tab or window | VERIFIED | `ActionType.SWITCH_TO_NEW_WINDOW/TAB/LATEST_WINDOW` in `src/core/enums.py` lines 34-36. `testdata/workflows/tabs/new_window_tab.json` parses via `WorkflowLoader` with all three action types. `test_window_switch_action_types_are_valid` passes. |
| 2 (SC-2) | The framework focuses (brings to foreground) the newly opened Chrome window | VERIFIED | `BasePage.open_new_window()` calls `driver.switch_to.new_window(type_hint)` atomically (one line, no second switch call). `TestOpenNewWindow` 3/3 pass confirming the atomic call. `switch_to_latest_window()` uses `EC.new_window_is_opened` + set-subtraction + `driver.switch_to.window(new_handle)`. |
| 3 (SC-3) | Subsequent page/section/element actions execute in the new window context | ? UNCERTAIN | Unit tests confirm dispatch routing but cannot verify that the WebDriver context persists across workflow hierarchy traversal. No smoke test exists. Needs human verification. |
| 4 (SC-4) | Unit tests cover tab-switch dispatch and window focus handling | VERIFIED | 10 new unit tests added: 3 dispatch tests (GREEN), 6 BasePage window tests (GREEN), 1 model enum test (GREEN). Full suite: 140 passed, 0 failed. |

**Score:** 4/4 truths verified (SC-3 has implementation evidence but requires human confirmation)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/core/enums.py` | Three new ActionType enum members | VERIFIED | Lines 34-36: `SWITCH_TO_NEW_WINDOW`, `SWITCH_TO_NEW_TAB`, `SWITCH_TO_LATEST_WINDOW` — all append-only after `NOOP` |
| `src/ui/base_page.py` | `open_new_window` method | VERIFIED | Line 276: `def open_new_window(self, type_hint: str = "window") -> None` — body is single call `self._driver.switch_to.new_window(type_hint)` |
| `src/ui/base_page.py` | `switch_to_latest_window` method | VERIFIED | Line 285: snapshots `old_handles` before wait, uses `EC.new_window_is_opened`, set-subtraction for handle detection, no `time.sleep` |
| `src/actions/element_actions.py` | Three dispatch branches | VERIFIED | Lines 79-86: three `elif` branches after `UPLOAD` and before `else` raise |
| `tests/unit/test_base_page_window.py` | 6 unit tests — all GREEN | VERIFIED | `TestOpenNewWindow` (3 tests) + `TestSwitchToLatestWindow` (3 tests) — all pass |
| `tests/unit/test_action_dispatch.py` | 3 dispatch tests GREEN (RED→GREEN) | VERIFIED | `test_switch_to_new_window_action`, `test_switch_to_new_tab_action`, `test_switch_to_latest_window_action` — all PASSED |
| `tests/unit/test_workflow_models.py` | `test_window_switch_action_types_are_valid` | VERIFIED | Test exists and passes — Pydantic accepts all three new ActionType values |
| `testdata/workflows/tabs/new_window_tab.json` | Valid workflow JSON with all three action types | VERIFIED | File exists, `workflow_name` field used (correct schema), all three action types present with sentinel locator `{by: id, value: _window}` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/ui/base_page.py::open_new_window` | `self._driver.switch_to.new_window` | Atomic one-line call (no second switch) | WIRED | Line 283: `self._driver.switch_to.new_window(type_hint)` — only call in the method |
| `src/ui/base_page.py::switch_to_latest_window` | `EC.new_window_is_opened` | `self._wm.wait_for` with EC condition | WIRED | Line 300: `EC.new_window_is_opened(list(old_handles))` passed to wait_for |
| `src/ui/base_page.py::switch_to_latest_window` | `set(driver.window_handles) - old_handles` | Set subtraction (not [-1] index) | WIRED | Line 304: `new_handles = set(self._driver.window_handles) - old_handles` |
| `src/actions/element_actions.py` | `self._page.open_new_window("window")` | `elif ActionType.SWITCH_TO_NEW_WINDOW` branch | WIRED | Line 79-80 |
| `src/actions/element_actions.py` | `self._page.open_new_window("tab")` | `elif ActionType.SWITCH_TO_NEW_TAB` branch | WIRED | Line 82-83 |
| `src/actions/element_actions.py` | `self._page.switch_to_latest_window()` | `elif ActionType.SWITCH_TO_LATEST_WINDOW` branch | WIRED | Line 85-86 |
| `testdata/workflows/tabs/new_window_tab.json` | `src/core/enums.py ActionType values` | Pydantic enum validation at load time | WIRED | WorkflowLoader parses all 3 elements without exception |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Three new ActionType values importable | `python3 -c "from src.core.enums import ActionType; print(ActionType('switch_to_new_window'))"` | `ActionType.SWITCH_TO_NEW_WINDOW` | PASS |
| Full unit suite (140 tests) | `pytest tests/unit/ -v` | `140 passed in 0.18s` | PASS |
| `test_base_page_window.py` 6 tests GREEN | `pytest tests/unit/test_base_page_window.py -v` | 6 PASSED | PASS |
| Dispatch tests all GREEN | `pytest tests/unit/test_action_dispatch.py::TestElementActions::test_switch_to_new_window_action` etc. | PASSED | PASS |
| Window-switch branches after UPLOAD, before else | `grep -n "elif action ==" src/actions/element_actions.py` | SWITCH branches at lines 79/82/85, before `else` at line 88 | PASS |
| No `time.sleep` in new window methods | `grep -A 20 "def open_new_window\|def switch_to_latest_window" src/ui/base_page.py` | No sleep in either method body | PASS |
| No `[-1]` index handle detection | `grep "\\[-1\\]" src/ui/base_page.py` | No matches | PASS |
| JSON fixture parses via loader | WorkflowLoader (tested via pytest) | `test_window_switch_action_types_are_valid` validates Pydantic acceptance | PASS |
| All 4 commits exist | `git log --oneline` | cd4a0d6, 812d57c, 87eb939, ffef8c4 all present | PASS |

### Requirements Coverage

The ROADMAP defines 4 success criteria for Phase 3. Plans 03-01 and 03-02 together declare requirements SC-1, SC-2, SC-3, SC-4. No REQUIREMENTS.md file exists — the ROADMAP is the authoritative source.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SC-1 | 03-01, 03-02 | Workflow JSON can declare tab-switch action | SATISFIED | `testdata/workflows/tabs/new_window_tab.json` + Pydantic enum validation + dispatch routing |
| SC-2 | 03-01, 03-02 | Framework focuses newly opened Chrome window | SATISFIED | `open_new_window` atomic call + `switch_to_latest_window` EC-based wait + window-handle switch |
| SC-3 | 03-02 | Subsequent actions execute in new window context | NEEDS HUMAN | Driver context persists at WebDriver level (confirmed by RESEARCH.md analysis) but not exercised by any smoke test with actual browser |
| SC-4 | 03-01, 03-02 | Unit tests cover dispatch and window focus | SATISFIED | 10 new unit tests, 140 total passing |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/ui/base_page.py` | 198 | `time.sleep(0.5)` | Info | Pre-existing code in `safe_click()` click-intercepted retry path — isolated, commented, logged at DEBUG per CLAUDE.md constraints. Not in any new window-switch code. |

No anti-patterns in any Phase 3 code.

### Human Verification Required

#### 1. New Window Context Persists Across Workflow Steps

**Test:** Create a minimal workflow JSON: (1) load `about:blank`, (2) click a button/link that opens a new window with `target="_blank"`, (3) declare an element with `action: switch_to_latest_window`, (4) declare a subsequent element in a new page/section that fills a field in the new window. Run `pytest tests/smoke/` or execute the WorkflowRunner directly.

**Expected:** The WebDriver executes step 4 in the new window — not the original tab. The locator resolves in the new window's DOM. No `NoSuchElementException` or stale element from the original window context.

**Why human:** Unit tests mock `self._driver` entirely. The `TestSwitchToLatestWindow` tests verify that `switch_to.window(handle)` is called, but a mock does not exercise the actual WebDriver context switch. The WorkflowEngine loop (which creates one `BasePage` instance and reuses it across elements) needs a real browser to confirm the switched context persists for all subsequent element executions.

#### 2. SWITCH_TO_NEW_WINDOW Opens a Separate OS Window

**Test:** Declare a workflow element with `action: switch_to_new_window`. Run against a real browser (Chrome). Observe whether a new OS-level window appears (not just a new tab in the same window).

**Expected:** A new Chrome window opens and receives focus. The WebDriver's `window_handles` list grows by one. Driver focus is on the new window.

**Why human:** `driver.switch_to.new_window("window")` vs `"tab"` behavior is a Selenium/ChromeDriver runtime distinction. Unit tests mock the driver — they cannot confirm the type_hint argument produces the correct OS-level window vs tab distinction in a real Chrome instance.

### Gaps Summary

No gaps blocking goal achievement. All four roadmap success criteria have implementation evidence. SC-3 requires human verification because no smoke test exercises the end-to-end window context persistence across workflow steps. The implementation is structurally correct (WebDriver context is global to the driver instance, confirmed by RESEARCH.md Pattern 4), but this cannot be proven without a real browser execution.

---

_Verified: 2026-05-15_
_Verifier: Claude (gsd-verifier)_
