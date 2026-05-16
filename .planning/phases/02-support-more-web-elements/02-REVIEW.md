---
phase: 02-support-more-web-elements
reviewed: 2026-05-15T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/core/enums.py
  - src/ui/base_page.py
  - src/actions/element_actions.py
  - tests/unit/test_base_page_select_radio.py
  - tests/unit/test_workflow_models.py
  - tests/unit/test_action_dispatch.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-15
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

This phase adds `NUMBER` and `EMAIL` to `ElementType` and `SELECT_RADIO` to `ActionType`, wires `select_radio` into `BasePage` and `ElementActions`, and covers the additions with unit tests. The design is consistent with existing patterns (`check`/`uncheck` parallel), the enum additions are clean, and the action dispatch is correctly integrated. No security vulnerabilities or data-loss risks were found.

Three warnings call out real behavioural gaps: `select_radio` does not scroll or wait for clickability (unlike every other click-producing method in the class), the `clear_and_type` implementation may silently truncate or corrupt numeric values typed into `<input type="number">` elements (via CONTROL+A / DELETE keystroke strategy), and the test helper `_make_page` leaves `page._readiness` unset, which would cause `AttributeError` on any test path that reaches `wait_for_page_ready`. Three lower-severity info items cover missing type-combo validation, unused `name` parameter in `select_radio`, and a test isolation pattern risk.

---

## Warnings

### WR-01: `select_radio` does not scroll into view or wait for clickable — inconsistent with framework contract

**File:** `src/ui/base_page.py:270-274`

**Issue:** Every other method that produces a click in `BasePage` follows the "scroll into view → wait clickable → click" sequence (`safe_click` at line 188). `select_radio` only calls `wait_for_visible` then `el.click()`. On AJAX-heavy pages this means:
1. The radio may be outside the viewport — the click may hit the wrong element or silently fail.
2. The element may be visible but not yet clickable (e.g., temporarily disabled while a spinner resolves) — the click will throw `ElementNotInteractableException` rather than waiting.

This is particularly relevant because radio buttons are frequently within dynamically-loaded form sections.

**Fix:** Mirror the `check`/`uncheck` pattern for simple cases but use `wait_for_clickable` rather than raw `wait_for_visible`:

```python
def select_radio(self, locator: LocatorDefinition, name: str = "") -> None:
    """Select a radio button if not already selected."""
    el = self.wait_for_visible(locator)
    if not el.is_selected():
        self.scroll_into_view(el)
        el = self.wait_for_clickable(locator)
        el.click()
```

---

### WR-02: `clear_and_type` CONTROL+A / DELETE sequence is unreliable for `<input type="number">` elements

**File:** `src/ui/base_page.py:207-230` (used by `ElementActions._do_input` for `NUMBER` type)

**Issue:** `<input type="number">` browsers reject non-numeric keys at the DOM level. The sequence `CONTROL+A` → `DELETE` → `send_keys(value)` works for text inputs, but for number inputs:
- Some WebDriver/browser combinations do not fire the `input` event correctly after `CONTROL+A`+`DELETE`.
- Sending `Keys.CONTROL + "a"` on a number input may not select all text in Firefox and Safari-based drivers.
- If the existing value is, for example, `"100"` and the new value is `"5"`, partial clearing can result in `"1005"` or `"005"` being submitted.

There is no special handling for `ElementType.NUMBER` in `_do_input`; it falls straight through to `clear_and_type`.

**Fix:** Add a number-specific clear strategy in `_do_input`, or add a `clear_via_js` fallback in `clear_and_type` when the element type attribute is `number`:

```python
def _do_input(self, element: ElementDefinition, value: Optional[Any]) -> None:
    str_value = str(value) if value is not None else ""
    trigger_change = bool(
        element.options and element.options.get("trigger_change_event")
    )
    if element.type == ElementType.NUMBER:
        # JS clear is more reliable for <input type="number">
        el = self.wait_for_visible(element.locator)
        self._page._driver.execute_script("arguments[0].value = '';", el)
        el.send_keys(str_value)
        if trigger_change:
            el.send_keys(Keys.TAB)
    else:
        self._page.clear_and_type(
            element.locator,
            str_value,
            element.name,
            trigger_change_event=trigger_change,
        )
```

Alternatively, at minimum document this known limitation so callers can use `trigger_change_event` and a `post_wait` assertion to detect stale values.

---

### WR-03: `_make_page()` in `test_base_page_select_radio.py` omits `_readiness`, causing `AttributeError` if any future test path reaches `wait_for_page_ready`

**File:** `tests/unit/test_base_page_select_radio.py:14-30`

**Issue:** The helper constructs a `BasePage` via `__new__` and sets `_driver`, `_wm`, and `_screenshots` but never sets `page._readiness`. The `BasePage.__init__` always creates `self._readiness = PageReadinessChecker(...)`. Any test that calls `wait_for_page_ready` on the returned object will raise `AttributeError: '_make_page' object has no attribute '_readiness'`. The current tests happen to avoid that path, but the helper is exported-quality fixture code that will break silently when extended.

**Fix:** Set `_readiness` to a `MagicMock()` in the helper, consistent with the other attributes:

```python
def _make_page():
    from src.ui.base_page import BasePage
    from unittest.mock import patch

    driver = MagicMock()
    wm = MagicMock()
    screenshots = MagicMock()

    with patch("src.ui.base_page.WaitManager"):
        page = BasePage.__new__(BasePage)
        page._driver = driver
        page._wm = wm
        page._screenshots = screenshots
        page._readiness = MagicMock()   # <-- add this
        return page
```

---

## Info

### IN-01: No model-level validation that `SELECT_RADIO` action is only used with `ElementType.RADIO`

**File:** `src/models/workflow_models.py:90-100` (cross-referenced with `src/core/enums.py`)

**Issue:** `ElementDefinition.value_required_for_input_actions` validates value presence but there is no validation enforcing that `action=SELECT_RADIO` is paired with `type=RADIO`. A JSON author could write `type=text, action=select_radio` and the model will accept it; the runtime will then try `el.is_selected()` on a text input, which is always `False`, so it will always click it without error — a silent behaviour mismatch.

The existing pattern does enforce action/type pairing implicitly (e.g., `SELECT_BY_TEXT` only makes semantic sense on `SELECT`/`MULTISELECT`), but a validator would catch authoring errors early and produce a better error message.

**Fix:** Add a cross-field validator in `ElementDefinition`:

```python
_RADIO_ACTIONS = {ActionType.SELECT_RADIO}
_RADIO_TYPES   = {ElementType.RADIO}

@model_validator(mode="after")
def action_type_compatibility(self) -> ElementDefinition:
    if self.action in _RADIO_ACTIONS and self.type not in _RADIO_TYPES:
        raise ValueError(
            f"Action '{self.action}' is only valid for type 'radio'; "
            f"got type '{self.type}'"
        )
    return self
```

---

### IN-02: `name` parameter accepted by `select_radio` but never used

**File:** `src/ui/base_page.py:270`

**Issue:** The method signature is `select_radio(self, locator, name="")` matching the rest of the API, but unlike `check`, `uncheck`, `safe_click`, and others, `name` is never logged or passed anywhere inside the method body. This is not a bug with the current code, but it means debug output for radio selection failures will be silent compared to click failures.

**Fix:** Add a debug log line consistent with the rest of the class:

```python
def select_radio(self, locator: LocatorDefinition, name: str = "") -> None:
    """Select a radio button if not already selected."""
    logger.debug("select_radio: '%s'", name)
    el = self.wait_for_visible(locator)
    if not el.is_selected():
        el.click()
```

---

### IN-03: `test_select_radio_already_selected` in `test_action_dispatch.py` calls `BasePage.select_radio` as an unbound method — fragile pattern

**File:** `tests/unit/test_action_dispatch.py:142-160`

**Issue:** The test calls `BasePage.select_radio(page, locator, "radio-1")` (unbound call with a `MagicMock(spec=BasePage)` as `self`). This bypasses the spec completely — `MagicMock(spec=BasePage)` will accept any attribute access, so the test does not actually verify that the real `select_radio` implementation is called, only that calling the real function body with a mock `self` works. The same behaviour is already tested more cleanly in `test_base_page_select_radio.py` using the `_make_page()` helper. The duplicate in `test_action_dispatch.py` adds test surface without adding coverage value, and it will silently pass even if `select_radio`'s body is replaced with `pass`.

**Fix:** Remove the duplicate unbound-method test from `test_action_dispatch.py:142-160` and rely on `TestSelectRadio` in `test_base_page_select_radio.py` for implementation verification. The dispatch test at line 137-140 (`test_select_radio_action`) is sufficient to verify routing.

---

_Reviewed: 2026-05-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
