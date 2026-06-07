# Phase 20: Support `first_valid` sentinel for `select_by_index` — Research

**Researched:** 2026-06-07
**Domain:** Selenium `Select` API, `BasePage.select_dropdown`, `ElementActions` dispatch
**Confidence:** HIGH (all findings from direct codebase inspection and live Selenium source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Triggered by a sentinel string value in the element's `value` field. Numeric
  values continue to work exactly as today (`Select(el).select_by_index(int(value))`).
- **D-02:** The sentinel keyword is `first_valid`, matched case-insensitively (`"first_valid"`,
  `"First_Valid"`, `"FIRST_VALID"` all trigger the behavior).
- **D-03:** "Validated" = the option's `value` attribute is non-empty. Scan options in DOM order
  and select the first one that qualifies.
- **D-04:** Whitespace-only values count as empty — strip the `value` attribute before checking,
  so `value="   "` is skipped just like `value=""`.
- **D-05:** Only the `value` attribute is considered. Disabled state and visible text are NOT
  part of the rule.
- **D-06:** If no option passes the validation rule, raise `ElementActionError` so the step is
  recorded as FAILED with a clear message. Not a graceful SKIP.

### Claude's Discretion
- Exact wording of the error message and log lines.
- Whether the sentinel detection lives in `element_actions.py` (before dispatch to
  `select_dropdown`) or inside `base_page.select_dropdown` — planner/executor's call.
- Whether to add a dedicated helper (e.g. `select_first_valid_option`) vs inline branch — as
  long as numeric `select_by_index` behavior is untouched.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. Stricter validation variants (skip-disabled, require
visible text) were explicitly rejected, not deferred.
</user_constraints>

---

## Summary

Phase 20 is a minimal, focused change: add a sentinel-value path to the existing
`select_by_index` action. When the element's resolved value is `"first_valid"` (case-insensitive),
the framework scans `<option>` elements via Selenium's `Select.options` list and clicks the
first whose `value` attribute, stripped of whitespace, is non-empty. All other values continue
through the existing `int(value)` path unchanged. If no option qualifies, the action raises
`ElementActionError` exactly as the existing unknown-`by` error does.

The entire change is contained in two source files: `src/ui/base_page.py` (add a branch or helper
inside `select_dropdown`) and/or `src/actions/element_actions.py` (sentinel detection before
dispatch). No schema changes, no new enum values, no new exception types are required. One new
unit test file is needed to cover the new behavior; the existing `test_action_dispatch.py` already
covers numeric `select_by_index` and must not regress.

**Primary recommendation:** Detect the sentinel inside `base_page.select_dropdown` (inside the
`elif by == "index":` branch, before the `int(value)` cast). This keeps all select-mode logic in
one method and avoids splitting the concern across two files. Add a private helper
`_select_first_valid_option(sel, name)` on `BasePage` for clarity and testability.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sentinel detection | UI base (`BasePage`) | — | All select-mode dispatch logic already lives in `select_dropdown`; consistent with existing "text"/"value"/"index" branching |
| Option scanning | UI base (`BasePage`) | — | Requires a live `Select` object; `BasePage` owns DOM interaction |
| Error raising | UI base (`BasePage`) | Action layer catches & re-wraps | `ElementActionError` is already raised from `select_dropdown` for unknown `by`; same pattern |
| Action dispatch routing | Action layer (`ElementActions`) | — | `SELECT_BY_INDEX` branch passes `str(value)` to `select_dropdown`; no change needed here |
| Test coverage | `tests/unit/` | — | No browser; mocked `Select.options` via `MagicMock` |

---

## Standard Stack

No new packages. All required libraries are already installed.

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| `selenium` | installed in `.venv` | `Select` object, `Select.options`, `opt.get_attribute("value")` | Already used |
| `pytest` | installed | test runner | Already used |
| `unittest.mock` | stdlib | `MagicMock` for option elements | Already used in all unit tests |

**Installation:** None required.

---

## Package Legitimacy Audit

> No new packages are installed in this phase.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
element.value = "first_valid"
        |
        v
ElementActions.execute()
  ACTION == SELECT_BY_INDEX
        |
        v
BasePage.select_dropdown(locator, "index", "first_valid", name)
        |
        v
  [index branch]
  value.strip().lower() == "first_valid"?
        |YES                      |NO
        v                         v
  _select_first_valid_option()  Select(el).select_by_index(int(value))
        |
  sel.options -> [opt, opt, ...]
        |
  for opt in options:
    attr = (opt.get_attribute("value") or "").strip()
    if attr:
      sel._set_selected(opt) / opt.click()
      return
        |
  no valid option found
        |
        v
  raise ElementActionError("No option with non-empty value ...", element_name=name)
```

### Recommended Project Structure

No new directories or files required outside of:
```
src/ui/base_page.py           # add branch/helper in select_dropdown
tests/unit/
└── test_base_page_select_first_valid.py   # new unit test file
```

### Pattern 1: Sentinel detection before int() cast (index branch)

**What:** Inside the `elif by == "index":` branch of `select_dropdown`, check whether the
value string is the sentinel before attempting `int(value)`. This avoids `ValueError` on
`int("first_valid")`.

**When to use:** Always — this is the only correct location because `int("first_valid")` raises
before we could branch anywhere else.

**Example (VERIFIED from codebase):**
```python
# Source: src/ui/base_page.py lines 258-259 (current)
elif by == "index":
    sel.select_by_index(int(value))

# After change:
elif by == "index":
    if value.strip().lower() == "first_valid":
        self._select_first_valid_option(sel, name)
    else:
        sel.select_by_index(int(value))
```

### Pattern 2: Option scanning helper using `Select.options`

**What:** Iterate `Select.options` (returns `list[WebElement]`, one per `<option>` tag in DOM
order), call `opt.get_attribute("value")` on each, strip whitespace, skip if falsy. Select the
first qualifying option by calling `opt.click()` directly (same mechanism Selenium's own
`_set_selected` uses).

**When to use:** When sentinel is detected.

**Key Selenium API facts (VERIFIED: live source at `.venv/lib/python3.14/site-packages/selenium/webdriver/support/select.py`):**
- `Select.options` → `self._el.find_elements(By.TAG_NAME, "option")` — returns all option
  elements in DOM order, no filtering.
- `opt.get_attribute("value")` — returns the HTML `value` attribute string, or `None` if the
  attribute is absent (an `<option>` without `value=` attribute inherits its text as the
  submitted value per HTML spec, but `get_attribute` returns `None` for the absent attribute).
  Treat `None` the same as empty string.
- `Select._set_selected(opt)` checks `is_enabled()` and calls `opt.click()`. To avoid calling a
  private method, calling `opt.click()` directly is also correct and is the simpler choice.

**Example:**
```python
# Source: derived from Select source at select.py lines 44-47, 87-101, 225-229
def _select_first_valid_option(self, sel: Select, name: str) -> None:
    """Select the first <option> whose value attribute is non-empty (stripped)."""
    for opt in sel.options:
        raw = opt.get_attribute("value")
        if raw is not None and raw.strip():
            opt.click()
            return
    raise ElementActionError(
        "No option with a non-empty value attribute found",
        element_name=name,
    )
```

### Pattern 3: `ElementActionError` shape (VERIFIED from codebase)

**What:** All select failures in `select_dropdown` raise `ElementActionError(message, element_name=name)`.
The two-argument form (message + keyword `element_name`) is the established pattern.

**Source:** `src/core/exceptions.py` lines 27-38; `src/ui/base_page.py` line 261:
```python
raise ElementActionError(f"Unknown select_by '{by}'", element_name=name)
```

The new no-valid-option error must use the same shape:
```python
raise ElementActionError(
    "No option with a non-empty value attribute found",
    element_name=name,
)
```

### Anti-Patterns to Avoid

- **Using `Select._set_selected()` directly:** It is a private method. Calling `opt.click()`
  achieves the same effect and is not an internal API. However, note that `_set_selected` also
  raises `NotImplementedError` if the option is disabled — since D-05 says disabled state is
  NOT considered, calling `opt.click()` directly is more faithful to the spec.
- **Using `get_dom_attribute("value")` instead of `get_attribute("value")`:** The project uses
  `get_attribute` consistently (see `src/waits/expected_states.py` lines 44, 57, 70; `select.py`
  line 41 uses `get_dom_attribute` only for the `multiple` attribute). Use `get_attribute("value")`
  to match project conventions.
- **Putting sentinel detection in `element_actions.py` only:** The `int()` cast is in
  `base_page.select_dropdown`, so the `ValueError` would already have been raised before control
  returns to `element_actions.py`. Detection must happen inside or before the `int()` call.
- **Caching `Select` objects across AJAX re-renders:** The `Select` object wraps a `WebElement`
  reference. Per CLAUDE.md, elements must not be cached across AJAX re-renders. Construct `sel`
  immediately before use (as the current code does) and do not store it as an instance attribute.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Iterating `<option>` elements | Custom JS `querySelectorAll` | `Select.options` property | Already returns `list[WebElement]` in DOM order; Selenium-native; handles shadow DOM correctly |
| Reading `value` attribute | Custom JS `getAttribute` | `opt.get_attribute("value")` | Project-standard; consistent with `expected_states.py` |
| Selecting an option | `driver.execute_script("arguments[0].selected = true", opt)` | `opt.click()` | click() triggers change/input events; JS assignment does not reliably trigger AJAX handlers |

---

## Common Pitfalls

### Pitfall 1: `int("first_valid")` raises `ValueError` before branching
**What goes wrong:** If sentinel detection happens after `int(value)`, a `ValueError` is raised
and caught by the outer `except Exception` in `ElementActions.execute()`, wrapping it in
`ElementActionError` with a confusing message ("invalid literal for int()").
**Why it happens:** The current index branch is a single line: `sel.select_by_index(int(value))`.
**How to avoid:** Check `value.strip().lower() == "first_valid"` BEFORE calling `int(value)`.
**Warning signs:** Test `test_select_by_index` passes but sentinel test raises `ValueError`.

### Pitfall 2: `opt.get_attribute("value")` returns `None` for options without `value=` attribute
**What goes wrong:** An `<option>` element that has no `value=` attribute at all returns `None`
from `get_attribute("value")`. If the code does `raw.strip()` without a `None` guard, it raises
`AttributeError: 'NoneType' object has no attribute 'strip'`.
**Why it happens:** HTML `<option>` elements are valid without a `value` attribute (the text
content is submitted instead). Selenium returns `None` for absent attributes from `get_attribute`.
**How to avoid:** Use `raw = opt.get_attribute("value")` then `if raw is not None and raw.strip()`.
**Warning signs:** `AttributeError` in tests with mock options that return `None`.

### Pitfall 3: Whitespace-only `value` must be skipped (D-04)
**What goes wrong:** An option with `value="   "` passes `if raw:` (non-empty string) but must
be treated as empty per D-04.
**Why it happens:** Python's truthiness treats any non-empty string as truthy.
**How to avoid:** Always `.strip()` before the truthiness check: `if raw is not None and raw.strip()`.
**Warning signs:** A test with `value="   "` selects the wrong option.

### Pitfall 4: `Select` wraps a stale element reference after AJAX re-render
**What goes wrong:** Between `wait_for_visible` (line 252) and iterating `sel.options`, the page
re-renders, making the original `WebElement` stale. `sel.options` calls `find_elements` on the
stale element and raises `StaleElementReferenceException`.
**Why it happens:** AJAX-heavy app; the `<select>` element itself may be re-inserted.
**How to avoid:** The existing `wait_for_visible` at the start of `select_dropdown` is the
correct mitigation. Do not add extra delays. If stale errors occur in practice, `ActionFactory`'s
existing `retryable` + `retry_count` mechanism handles re-running the full action.
**Warning signs:** Intermittent `StaleElementReferenceException` in smoke tests.

### Pitfall 5: `select_by_index` currently uses `opt.get_attribute("index")`, NOT position
**What goes wrong:** `Select.select_by_index(n)` does NOT select the nth element by list
position; it selects the element whose HTML `index` attribute equals `str(n)` (see
`select.py` lines 87-101). This is a Selenium subtlety.
**Why it happens:** The Selenium `Select.select_by_index` implementation matches on the `index`
attribute, not the list position. For well-formed HTML, `index` usually equals list position,
but they can differ.
**How to avoid:** The new sentinel code iterates `sel.options` by list position (DOM order),
which is the correct interpretation of "first option in DOM order". This is intentionally
different from `select_by_index`'s attribute-matching. No change needed — the sentinel behavior
is to scan by DOM order, which `sel.options` provides directly.
**Warning signs:** None — the two behaviors are intended to be different.

---

## Code Examples

### Complete updated `select_dropdown` and helper (verified patterns)

```python
# Source: src/ui/base_page.py — current lines 237-261 + additions
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
        value: The option text, value, index string, or sentinel ``'first_valid'``.
        name: Element name for logging.
    """
    el = self.wait_for_visible(locator)
    sel = Select(el)
    if by == "text":
        sel.select_by_visible_text(value)
    elif by == "value":
        sel.select_by_value(value)
    elif by == "index":
        if value.strip().lower() == "first_valid":
            self._select_first_valid_option(sel, name)
        else:
            sel.select_by_index(int(value))
    else:
        raise ElementActionError(f"Unknown select_by '{by}'", element_name=name)


def _select_first_valid_option(self, sel: Select, name: str) -> None:
    """Select the first <option> whose value attribute is non-empty after stripping.

    "Non-empty" means the value attribute exists and is not blank/whitespace-only.
    Options are scanned in DOM order (the order returned by Select.options).

    Args:
        sel: A Selenium Select wrapping the visible <select> element.
        name: Element name for error reporting.

    Raises:
        ElementActionError: If no option has a non-empty value attribute.
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

### JSON workflow usage shape
```json
{
  "name": "Account Type",
  "type": "select",
  "action": "select_by_index",
  "value": "first_valid",
  "locator": { "by": "id", "value": "account-type" }
}
```

### Test mock pattern for Select.options (established from test_action_dispatch.py)
```python
# Source: tests/unit/test_action_dispatch.py pattern + Selenium Select structure
from unittest.mock import MagicMock, patch
from selenium.webdriver.support.select import Select
from src.ui.base_page import BasePage
from src.core.exceptions import ElementActionError

def _make_mock_option(value_attr):
    """Returns a mock <option> element with given value attribute."""
    opt = MagicMock()
    opt.get_attribute.side_effect = lambda attr: value_attr if attr == "value" else None
    return opt

def _make_page_with_select(options_value_attrs):
    """Construct a BasePage with a mocked Select whose options have given value attrs."""
    driver = MagicMock()
    wm = MagicMock()
    mock_select_el = MagicMock()
    mock_select_el.tag_name = "select"
    mock_select_el.get_dom_attribute.return_value = None  # not multiple
    mock_options = [_make_mock_option(v) for v in options_value_attrs]
    mock_select_el.find_elements.return_value = mock_options

    page = BasePage(driver, wm)
    locator = LocatorDefinition(by="id", value="sel")
    page.wait_for_visible = MagicMock(return_value=mock_select_el)
    return page, locator
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Numeric-only `select_by_index` | Sentinel `first_valid` adds first-valid-value mode | No regression to numeric path; additive only |

**No deprecated APIs used.** `Select.options`, `get_attribute("value")`, and `opt.click()` are
stable Selenium APIs present across Selenium 3, 4, and the installed version.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `opt.click()` reliably triggers JS change/input events on `<option>` elements in all target browsers | Don't Hand-Roll | If click doesn't trigger events, AJAX-dependent dropdowns may not respond — mitigation: existing `post_wait` support handles this case |

All other claims are VERIFIED from direct inspection of the installed codebase and Selenium source.

---

## Open Questions

1. **Should `_select_first_valid_option` be a private method on `BasePage` or an inline branch?**
   - What we know: The existing code has precedent for both (inline branches like `check()`
     and private helpers like `retry_on_stale()`).
   - What's unclear: Team preference.
   - Recommendation: Private helper — it has its own loop logic and error raise; a helper makes
     it independently testable via `BasePage._select_first_valid_option(mock_sel, "name")`.

2. **Should `element_actions.py` pass `"first_valid"` through unchanged or normalize to lowercase?**
   - What we know: Value arrives as `str(value)` (line 65 of `element_actions.py`); the sentinel
     check in `select_dropdown` does `value.strip().lower()` — so normalization happens in
     `base_page.py`.
   - Recommendation: No change to `element_actions.py`; `select_dropdown` handles
     case-insensitive matching internally. Keeps the dispatch layer ignorant of sentinel semantics.

---

## Environment Availability

Step 2.6: SKIPPED — no external dependencies. All required Selenium and pytest infrastructure
is already installed in `.venv`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (installed; currently 394 tests passing) |
| Config file | `pytest.ini` |
| Quick run command | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py -x` |
| Full suite command | `.venv/bin/pytest tests/unit/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FV-01 | `select_dropdown(..., "index", "first_valid", name)` selects the first option with non-empty value | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_selects_first_non_empty_value_option -x` | ❌ Wave 0 |
| FV-02 | Case-insensitive sentinel: `"FIRST_VALID"` and `"First_Valid"` both trigger the mode | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_sentinel_case_insensitive -x` | ❌ Wave 0 |
| FV-03 | Whitespace-only `value` attribute is skipped (D-04) | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_whitespace_value_skipped -x` | ❌ Wave 0 |
| FV-04 | Empty-string `value` attribute is skipped | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_empty_string_value_skipped -x` | ❌ Wave 0 |
| FV-05 | `None` return from `get_attribute("value")` is skipped (no `AttributeError`) | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_none_value_attribute_skipped -x` | ❌ Wave 0 |
| FV-06 | No qualifying option raises `ElementActionError` (D-06) | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_no_valid_option_raises -x` | ❌ Wave 0 |
| FV-07 | Numeric `select_by_index` path is untouched (regression guard) | unit | `.venv/bin/pytest tests/unit/test_action_dispatch.py::TestElementActions::test_select_by_index -x` | ✅ exists |
| FV-08 | `ElementActions.execute()` passes `"first_valid"` string through to `select_dropdown` unchanged | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_dispatch_passes_sentinel_to_select_dropdown -x` | ❌ Wave 0 |
| FV-09 | Options are scanned in DOM order; first qualifying is selected, not last | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_first_valid_in_dom_order -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py -x`
- **Per wave merge:** `.venv/bin/pytest tests/unit/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_base_page_select_first_valid.py` — covers FV-01..FV-06, FV-08, FV-09

*FV-07 is already covered by `test_action_dispatch.py::TestElementActions::test_select_by_index`.
No new framework config or fixtures needed.*

---

## Security Domain

This phase has no authentication, session, access control, cryptography, or user-supplied data
injection concerns. The sentinel value is a constant string comparison in application code, not
user input reaching the browser's DOM. ASVS categories V2–V6 do not apply.

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `src/ui/base_page.py` lines 237–261 — `select_dropdown` current implementation; `Select` import
- `src/actions/element_actions.py` lines 64–65 — `SELECT_BY_INDEX` dispatch
- `src/core/exceptions.py` lines 27–38 — `ElementActionError` constructor signature and pattern
- `.venv/lib/python3.14/site-packages/selenium/webdriver/support/select.py` lines 44–47, 87–101, 225–229 — `Select.options`, `select_by_index`, `_set_selected`
- `tests/unit/test_action_dispatch.py` lines 94–103 — existing `SELECT_BY_INDEX` test (regression anchor)
- `tests/unit/test_base_page_select_radio.py` — established pattern for `BasePage` unit tests
- `.planning/phases/19-support-page-skip-on-disable-class/19-PATTERNS.md` — established phase PATTERNS.md format
- `.planning/phases/19-support-page-skip-on-disable-class/19-VALIDATION.md` — established VALIDATION.md format

### Secondary (MEDIUM confidence)
- `src/waits/expected_states.py` lines 44, 57, 70 — confirms project uses `get_attribute("value")` not `get_dom_attribute`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; Selenium source inspected directly
- Architecture: HIGH — all touch points verified in codebase; `Select.options` API confirmed
- Pitfalls: HIGH — derived from direct Selenium source reading and project code patterns

**Research date:** 2026-06-07
**Valid until:** Stable — Selenium `Select` API has not changed shape across versions 3/4/4.x
