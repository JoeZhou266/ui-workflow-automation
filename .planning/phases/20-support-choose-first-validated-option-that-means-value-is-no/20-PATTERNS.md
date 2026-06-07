# Phase 20: Support `first_valid` Sentinel for `select_by_index` — Pattern Map

**Mapped:** 2026-06-07
**Files analyzed:** 2 (1 modified, 1 new)
**Analogs found:** 2 / 2

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/ui/base_page.py` | UI base method | request-response (DOM interaction) | `src/ui/base_page.py` `select_dropdown()` (lines 237–261) + `ElementActionError` raise (line 261) | exact |
| `tests/unit/test_base_page_select_first_valid.py` | unit test | — | `tests/unit/test_base_page_select_radio.py` (BasePage unit-test structure) + `tests/unit/test_action_dispatch.py` (mock fixture pattern + `select_by_index` regression anchor) | exact |

---

## Pattern Assignments

### `src/ui/base_page.py` — add sentinel branch + `_select_first_valid_option` (UI base, request-response)

**Analog:** `src/ui/base_page.py` `select_dropdown()` (lines 237–261) and `_select_first_valid_option()` will sit immediately after it.

**Imports pattern** — no new imports needed (lines 1–26):
```python
from __future__ import annotations
# Already present:
from selenium.webdriver.support.select import Select          # line 14
from src.core.exceptions import ElementActionError            # line 17
from src.core.logger import get_logger                        # line 18
# get_logger is already called: logger = get_logger("base_page")  # line 26
```

**Existing `select_dropdown` core pattern** (lines 237–261) — full method to replace:
```python
def select_dropdown(
    self,
    locator: LocatorDefinition,
    by: str,
    value: str,
    name: str = "",
) -> None:
    """Select a ``<select>`` option.

    Args:
        locator: Select element locator.
        by: One of ``'text'``, ``'value'``, or ``'index'``.
        value: The option text, value, or index string.
        name: Element name for logging.
    """
    el = self.wait_for_visible(locator)
    sel = Select(el)
    if by == "text":
        sel.select_by_visible_text(value)
    elif by == "value":
        sel.select_by_value(value)
    elif by == "index":
        sel.select_by_index(int(value))    # <-- sentinel branch goes here
    else:
        raise ElementActionError(f"Unknown select_by '{by}'", element_name=name)
```

**Updated `select_dropdown` index branch** (replace lines 258–259 only):
```python
    elif by == "index":
        if value.strip().lower() == "first_valid":
            self._select_first_valid_option(sel, name)
        else:
            sel.select_by_index(int(value))
```

**Key rule:** The sentinel check (`value.strip().lower() == "first_valid"`) MUST precede the `int(value)` cast. `int("first_valid")` raises `ValueError` immediately; if the cast ran first the outer `except Exception` in `ElementActions.execute()` would wrap it in a confusing `ElementActionError`.

**`ElementActionError` failure pattern** (line 261) — the shape to mirror for the no-valid-option case:
```python
raise ElementActionError(f"Unknown select_by '{by}'", element_name=name)
```
The two-argument form — positional message string, keyword `element_name=name` — is the established shape in this file. The new raise uses the same form.

**New private helper `_select_first_valid_option`** — add directly after `select_dropdown`:
```python
def _select_first_valid_option(self, sel: Select, name: str) -> None:
    """Select the first <option> whose value attribute is non-empty after stripping.

    "Non-empty" means the value attribute exists and is not blank/whitespace-only
    (D-03, D-04). Options are scanned in DOM order (the order returned by
    Select.options). Disabled state and visible text are NOT considered (D-05).

    Args:
        sel: A Selenium Select wrapping the visible <select> element.
        name: Element name for error reporting.

    Raises:
        ElementActionError: If no option has a non-empty value attribute (D-06).
    """
    for opt in sel.options:
        raw = opt.get_attribute("value")
        if raw is not None and raw.strip():
            logger.debug(
                "select first_valid: found option with value='%s' for '%s'",
                raw.strip(), name,
            )
            opt.click()
            return
    raise ElementActionError(
        "No option with a non-empty value attribute found",
        element_name=name,
    )
```

**Selenium API facts (verified):**
- `Select.options` calls `self._el.find_elements(By.TAG_NAME, "option")` — returns all options in DOM order, no filtering.
- `opt.get_attribute("value")` returns the HTML `value` attribute string, or `None` if the attribute is absent on the element. Guard against `None` before `.strip()`.
- `opt.click()` is the correct selection mechanism (not the private `Select._set_selected()`); it triggers JS `change`/`input` events that AJAX-heavy pages rely on.
- Use `get_attribute("value")` not `get_dom_attribute("value")` — the project uses `get_attribute` consistently (confirmed in `src/waits/expected_states.py` lines 44, 57, 70).

**Private helper pattern** — precedent for private helpers on `BasePage` is established at `retry_on_stale()` (lines 389–412). Place `_select_first_valid_option` immediately after `select_dropdown`, in the "Interactions" section.

---

### `tests/unit/test_base_page_select_first_valid.py` — new unit test file (test, no browser)

**Analog 1:** `tests/unit/test_base_page_select_radio.py` — `BasePage` unit-test structure: `_make_page()` helper, `TestSelectRadio` class, `wait_for_visible` mock injection.
**Analog 2:** `tests/unit/test_action_dispatch.py` — `_make_locator()` helper (line 14), `test_select_by_index` dispatch test (lines 94–103), `pytest.raises(ElementActionError)` pattern (lines 132–136).

**`_make_page()` helper pattern** (from `test_base_page_select_radio.py`, lines 14–30):
```python
def _make_page():
    """Return a minimal mock that exercises the real select_radio implementation."""
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
        return page
```

**Alternative instantiation pattern** (from `test_action_dispatch.py` lines 145–149 and `test_page_skip_disable_class.py` lines 388–390) — direct construction also works when `WaitManager` is mocked via the constructor:
```python
driver = MagicMock()
wm = MagicMock()
page = BasePage(driver, wm)
page.wait_for_visible = MagicMock(return_value=mock_select_el)
```
Use whichever is cleaner; inject `wait_for_visible` via `MagicMock` in both cases.

**Mock `<option>` element helper pattern** (from RESEARCH.md verified pattern):
```python
def _make_mock_option(value_attr):
    """Returns a mock <option> element with given get_attribute('value') return."""
    opt = MagicMock()
    opt.get_attribute.side_effect = lambda attr: value_attr if attr == "value" else None
    return opt
```

**Mock `Select` construction pattern** — `Select.__init__` takes a `WebElement`; its `.options` property calls `find_elements(By.TAG_NAME, "option")` on that element. To mock it without a real browser:
```python
mock_select_el = MagicMock()
mock_select_el.tag_name = "select"
mock_select_el.get_dom_attribute.return_value = None   # not a multiple-select
mock_options = [_make_mock_option(v) for v in value_attrs]
mock_select_el.find_elements.return_value = mock_options
```
Then `Select(mock_select_el).options` returns `mock_options`.

**`test_select_by_index` regression anchor** (from `test_action_dispatch.py`, lines 94–103) — this test is the FV-07 regression guard and must remain passing unchanged:
```python
def test_select_by_index(self, executor, mock_page):
    el = _make_element(
        etype=ElementType.SELECT,
        action=ActionType.SELECT_BY_INDEX,
        value="2",
    )
    executor.execute(el, value="2")
    mock_page.select_dropdown.assert_called_once_with(
        el.locator, "index", "2", el.name
    )
```

**`ElementActionError` raise test pattern** (from `test_action_dispatch.py`, lines 132–136):
```python
with pytest.raises(ElementActionError, match="No file path"):
    executor.execute(el, value=None)
```
Mirror for FV-06:
```python
with pytest.raises(ElementActionError, match="non-empty value attribute"):
    page._select_first_valid_option(sel, "my-select")
```

**New test file header and imports pattern** (from `test_base_page_select_radio.py`, lines 1–7):
```python
"""Unit tests for BasePage._select_first_valid_option() and select_dropdown first_valid sentinel."""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from src.models.workflow_models import LocatorDefinition
from src.ui.base_page import BasePage
from src.core.exceptions import ElementActionError
from selenium.webdriver.support.select import Select
```

**Test class structure** (FV-01 through FV-09 map):

| Test method | Req ID | What it exercises |
|---|---|---|
| `test_selects_first_non_empty_value_option` | FV-01 | Happy path: `[None, "", "real"]` → selects third option |
| `test_sentinel_case_insensitive` | FV-02 | `"FIRST_VALID"` and `"First_Valid"` both reach the helper |
| `test_whitespace_value_skipped` | FV-03 | Option with `value="   "` is skipped |
| `test_empty_string_value_skipped` | FV-04 | Option with `value=""` is skipped |
| `test_none_value_attribute_skipped` | FV-05 | Option returning `None` from `get_attribute` is skipped without `AttributeError` |
| `test_no_valid_option_raises` | FV-06 | All options invalid → `ElementActionError` raised |
| `test_first_valid_in_dom_order` | FV-09 | First qualifying option is selected, not the last |
| `test_dispatch_passes_sentinel_to_select_dropdown` | FV-08 | `ElementActions.execute()` passes `"first_valid"` string unchanged to `select_dropdown` |

FV-07 (`test_select_by_index`) already exists in `test_action_dispatch.py` — do not duplicate.

---

## Shared Patterns

### `ElementActionError` two-argument raise
**Source:** `src/ui/base_page.py` line 261; `src/core/exceptions.py` lines 27–39
**Apply to:** `_select_first_valid_option` failure path
```python
# Constructor: ElementActionError(message: str, element_name: str = "", action: str = "")
# Established shape in select_dropdown:
raise ElementActionError(f"Unknown select_by '{by}'", element_name=name)
# New raise mirrors this exactly:
raise ElementActionError(
    "No option with a non-empty value attribute found",
    element_name=name,
)
```

### Private helper method on `BasePage`
**Source:** `src/ui/base_page.py` `retry_on_stale()` (lines 389–412)
**Apply to:** `_select_first_valid_option()`
```python
# Naming: underscore prefix, concise verb phrase
# Placement: "Interactions" section, after the public method it supports
# Docstring: describes invariants + raises clause
# No instance-attribute caching of DOM objects (CLAUDE.md constraint)
```

### `from __future__ import annotations`
**Source:** Every source file in `src/` and `tests/` (project-wide convention, CLAUDE.md)
**Apply to:** Both modified/new files.

### MagicMock `wait_for_visible` injection
**Source:** `tests/unit/test_base_page_select_radio.py` lines 38–39; `test_action_dispatch.py` lines 148–149
**Apply to:** All test methods in `test_base_page_select_first_valid.py`
```python
page.wait_for_visible = MagicMock(return_value=mock_select_el)
```
This replaces the real wait entirely so no browser or `WaitManager` is needed.

---

## No Analog Found

All 2 files have close codebase analogs. No files require falling back to external pattern documentation.

---

## Metadata

**Analog search scope:** `src/ui/`, `src/actions/`, `src/core/`, `tests/unit/`
**Files scanned:** 5 (`base_page.py`, `element_actions.py`, `exceptions.py`, `test_action_dispatch.py`, `test_base_page_select_radio.py`)
**Pattern extraction date:** 2026-06-07
