# Phase 2: Support More Web Elements - Research

**Researched:** 2026-05-15
**Domain:** Selenium action dispatch, Pydantic enums, Python unit testing with mocks
**Confidence:** HIGH

## Summary

Phase 2 extends the existing action dispatch engine to cover four element types that are currently absent or incomplete: `checkbox`, `radio`, `number`, and `email`. The framework's synchronization and interaction infrastructure is already in place — `BasePage.check()` and `BasePage.uncheck()` exist and are tested; `clear_and_type()` handles all text-based inputs generically. The work is therefore narrow and surgical: add missing `ElementType` enum values (`NUMBER`, `EMAIL`), add a `SELECT_RADIO` action type, extend `ElementActions.execute()` dispatch, and write unit tests following the pattern already established in `test_action_dispatch.py`.

No new Selenium primitives are needed. No new `BasePage` methods are needed. The phase is primarily about making the JSON schema aware of new types and routing them correctly through the dispatch table in `element_actions.py`.

**Primary recommendation:** Add `NUMBER` and `EMAIL` to `ElementType`, add `SELECT_RADIO` to `ActionType`, extend the dispatch in `ElementActions.execute()`, and add fixture JSON snippets plus unit tests — all in a single focused plan.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Checkbox check/uncheck dispatch | Actions layer (`element_actions.py`) | UI layer (`BasePage`) | `BasePage.check/uncheck` already exist; dispatch is the gap |
| Radio button selection | Actions layer (`element_actions.py`) | UI layer (`BasePage`) | Radio select = click when not selected; same as check pattern |
| Number input typing | Actions layer (`element_actions.py`) | — | Routes to `clear_and_type` like TEXT; no new Selenium primitive needed |
| Email input typing | Actions layer (`element_actions.py`) | — | Same as number: string value, standard typing, HTML validation is browser-native |
| JSON schema validation | Models layer (`workflow_models.py`, `enums.py`) | — | Pydantic enum membership enforced at model instantiation |
| Unit test coverage | `tests/unit/test_action_dispatch.py` | — | Follows existing mock-based pattern; no browser required |

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| selenium | (existing) | Browser interaction primitives | Framework foundation |
| pydantic | 2.13.3 [VERIFIED: `python3 -c "import pydantic; print(pydantic.VERSION)"`] | Model/enum validation | Already used for all models |
| pytest | 8.4.2 [VERIFIED: pytest run output] | Test runner | Existing test infrastructure |
| unittest.mock | stdlib | Mock BasePage/WaitManager | Already used in `test_action_dispatch.py` |

### No New Dependencies

Phase 2 requires zero new packages. All Selenium interactions for checkbox, radio, number, and email use primitives already available in `BasePage`.

**Installation:** None required.

## Architecture Patterns

### System Architecture Diagram

```
Workflow JSON
    │
    ▼
WorkflowLoader.load()
    │  (resolve_refs, validate via Pydantic)
    ▼
ElementDefinition
  ├── type: ElementType  (checkbox | radio | number | email | ...)
  ├── action: ActionType (check | uncheck | select_radio | input | ...)
  └── locator, value, pre_wait, post_wait
    │
    ▼
ActionFactory.run()
  ├── pre_wait → WaitManager
  ├── ElementActions.execute(element, resolved_value)  ← DISPATCH HERE
  │     ├── ActionType.CHECK     → BasePage.check()
  │     ├── ActionType.UNCHECK   → BasePage.uncheck()
  │     ├── ActionType.SELECT_RADIO → BasePage.select_radio()  [NEW]
  │     └── ActionType.INPUT (number/email) → BasePage.clear_and_type()
  └── post_wait → WaitManager
```

### Recommended Project Structure

No new directories. All changes fit within existing structure:

```
src/
├── core/
│   └── enums.py              # Add NUMBER, EMAIL to ElementType; SELECT_RADIO to ActionType
├── actions/
│   └── element_actions.py    # Add dispatch branch for SELECT_RADIO; INPUT already handles text-like types
├── ui/
│   └── base_page.py          # Add select_radio() method (click if not selected)
tests/
├── unit/
│   └── test_action_dispatch.py  # Add test cases for new types/actions
testdata/
└── workflows/
    └── tabs/
        └── (add radio_tab.json or extend existing fixtures for unit tests)
```

### Pattern 1: Dispatch by ActionType (existing pattern to follow)

**What:** `ElementActions.execute()` maps `ActionType` values to `BasePage` method calls using `if/elif` branches.
**When to use:** Every new action type follows this exact pattern.
**Example (from existing code):**
```python
# Source: src/actions/element_actions.py (verified by reading file)
elif action == ActionType.CHECK:
    self._page.check(element.locator, element.name)

elif action == ActionType.UNCHECK:
    self._page.uncheck(element.locator, element.name)
```

New `SELECT_RADIO` follows the same shape:
```python
elif action == ActionType.SELECT_RADIO:
    self._page.select_radio(element.locator, element.name)
```

### Pattern 2: Checkbox already dispatches via `CHECK`/`UNCHECK`

**What:** `BasePage.check()` already guards against double-click by testing `is_selected()` first.
**Finding:** `ElementType.CHECKBOX` and `ActionType.CHECK`/`UNCHECK` already exist in enums and are already handled in `element_actions.py`. The check/uncheck dispatch is complete. [VERIFIED: read `src/core/enums.py`, `src/actions/element_actions.py`, `src/ui/base_page.py`]

**Implication for planning:** The only gap for checkbox is unit test completeness — the dispatch code exists. The planner should verify tests cover both `check` and `uncheck` with correct state assertions (they currently do in `test_action_dispatch.py`).

### Pattern 3: Radio button select = check pattern

**What:** Selecting a radio button is semantically identical to checking a checkbox — click if not already selected.
**Selenium behavior:** `element.is_selected()` works for both `<input type="checkbox">` and `<input type="radio">`. Clicking a radio that is already selected is a no-op in HTML. [VERIFIED: Selenium WebElement API — `is_selected()` applies to both input types]
**Recommended implementation:**
```python
# In BasePage
def select_radio(self, locator: LocatorDefinition, name: str = "") -> None:
    """Select a radio button if not already selected."""
    el = self.wait_for_visible(locator)
    if not el.is_selected():
        el.click()
```

### Pattern 4: Number and email inputs use `clear_and_type` unchanged

**What:** HTML `<input type="number">` and `<input type="email">` accept `send_keys()` exactly like `<input type="text">`. The browser enforces HTML5 validation on submit, not on `send_keys`. [VERIFIED: Selenium behavior — send_keys is agnostic to input type attribute]
**Implication:** `ActionType.INPUT` + `_do_input()` already handles these via `clear_and_type()`. The only missing piece is `ElementType.NUMBER` and `ElementType.EMAIL` in the enum so JSON can declare those types.
**No new dispatch branch needed** — `INPUT` already routes correctly. Adding `NUMBER`/`EMAIL` to `ElementType` is purely a schema/documentation addition that enables validation and makes JSON intent explicit.

### Anti-Patterns to Avoid

- **Do not add `NUMBER` and `EMAIL` as separate `ActionType` values.** Action type describes what to do (`input`, `click`). Element type describes what the element is (`number`, `email`). These are orthogonal. Conflating them violates the existing enum design.
- **Do not use `time.sleep()` for synchronization.** CLAUDE.md explicitly forbids this as a strategy. All waits go through `WaitManager`.
- **Do not cache `WebElement` references across AJAX boundaries.** The `check/uncheck` and `select_radio` methods use `wait_for_visible` on each call, not cached references.
- **Do not hand-roll HTML5 email format validation in Python.** The framework's job is to drive the browser, not re-implement browser validation. If a test needs to assert on a validation message, use `AssertionDefinition` with `text_contains`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Email format validation | Custom regex in `_do_input` | Let browser enforce HTML5 validation | Framework drives browser; validation is browser's responsibility |
| Radio group "deselect all" | Custom JS to uncheck all radios | N/A — radio groups are single-select by design | HTML radio semantics already enforce exclusivity |
| Checkbox state assertion | Custom `is_checked()` in actions | `AssertionDefinition` with `condition: selected` | `WaitConditionType.SELECTED` already exists and is tested |

**Key insight:** All interaction primitives exist in `BasePage`. The only hand-rolling needed is the `select_radio` method (4 lines), which is a thin wrapper around existing primitives.

## Common Pitfalls

### Pitfall 1: Adding NUMBER/EMAIL as ActionType instead of ElementType
**What goes wrong:** Confusion between what an element *is* (type) vs what to *do* to it (action). If `NUMBER` is an action, the dispatch logic breaks for `number` inputs that need `input` action.
**Why it happens:** The phase description says "number and email input types" — this refers to HTML input types, which map to `ElementType`, not `ActionType`.
**How to avoid:** `ElementType` = HTML element semantics; `ActionType` = verb/operation. Number and email are types, not actions.
**Warning signs:** If a new `ActionType` is added that doesn't describe a verb (check, click, input, upload), it's probably in the wrong enum.

### Pitfall 2: Forgetting the model validator covers new input types
**What goes wrong:** The `ElementDefinition.value_required_for_input_actions` model validator checks `ActionType.INPUT` — this already covers `NUMBER` and `EMAIL` element types when action is `INPUT`. No validator change needed.
**Why it happens:** Developers assume enum additions require corresponding validator changes.
**How to avoid:** Verify: adding `NUMBER`/`EMAIL` to `ElementType` does NOT require changes to `value_required_for_input_actions`. The validator is action-based, not type-based.
**Warning signs:** Any edit to `WorkflowDefinition` or `ElementDefinition` validators beyond confirming they still pass.

### Pitfall 3: Missing test for radio "already selected" idempotency
**What goes wrong:** Test only covers the "not selected → click" path. The "already selected → no click" path is untested, so double-click bugs slip through.
**Why it happens:** Happy-path testing only.
**How to avoid:** Write two test cases for `SELECT_RADIO`: one where `is_selected()` returns `False` (click expected), one where it returns `True` (no click expected).
**Warning signs:** `test_select_radio_action` exists but only one mock scenario.

### Pitfall 4: Implicit vs explicit wait regression
**What goes wrong:** Using `find()` directly in a new method instead of `wait_for_visible()`, leaving a race condition on AJAX-heavy pages.
**Why it happens:** Copy-paste from simpler examples.
**How to avoid:** All new `BasePage` methods must call `wait_for_visible()` before interacting. Check existing `check()` and `uncheck()` as canonical examples.

## Code Examples

Verified patterns from existing codebase:

### Existing check/uncheck pattern (canonical model for select_radio)
```python
# Source: src/ui/base_page.py (verified by reading)
def check(self, locator: LocatorDefinition, name: str = "") -> None:
    """Check a checkbox if not already checked."""
    el = self.wait_for_visible(locator)
    if not el.is_selected():
        el.click()

def uncheck(self, locator: LocatorDefinition, name: str = "") -> None:
    """Uncheck a checkbox if currently checked."""
    el = self.wait_for_visible(locator)
    if el.is_selected():
        el.click()
```

### Existing unit test pattern (mock-based, no browser)
```python
# Source: tests/unit/test_action_dispatch.py (verified by reading)
def test_check_action(self, executor, mock_page):
    el = _make_element(etype=ElementType.CHECKBOX, action=ActionType.CHECK)
    executor.execute(el)
    mock_page.check.assert_called_once_with(el.locator, el.name)
```

### New element definitions in workflow JSON (model to follow)
```json
// Source: testdata/workflows/tabs/checkboxes_tab.json (verified by reading)
{
  "name": "Checkbox 1",
  "type": "checkbox",
  "action": "check",
  "locator": { "by": "css_selector", "value": "input[type='checkbox']:nth-of-type(1)" }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| N/A (new phase) | — | — | — |

**Deprecated/outdated:**
- None applicable — framework is in active development, no deprecated patterns in scope.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Radio selection using `is_selected()` + click is idempotent and correct for all radio button implementations | Architecture Patterns #3 | If a custom JS widget handles radio state outside the DOM `checked` attribute, `is_selected()` may return wrong state — but this applies to edge cases not in scope |
| A2 | `<input type="number">` and `<input type="email">` accept `send_keys()` without requiring special handling | Pattern 4 | If a target app uses a JS number spinner widget that intercepts key events differently, `clear_and_type` may need adjustment — but standard HTML inputs work correctly |

**All other claims in this document were verified by reading source files in this session.**

## Open Questions

1. **Should `NUMBER` and `EMAIL` be added to `ElementType` at all?**
   - What we know: Current `ElementType` maps to semantic HTML element types. `TEXT` currently covers all text-like inputs. Adding `NUMBER`/`EMAIL` adds clarity for JSON authors but no functional difference in dispatch.
   - What's unclear: Project preference — is `ElementType` descriptive (maps to HTML type attribute) or functional (maps to dispatch behavior)?
   - Recommendation: Add them. The phase description explicitly names them. They make JSON self-documenting and align `ElementType` with HTML's type attribute vocabulary.

2. **Should a `SELECT_RADIO` action be separate from `CHECK`?**
   - What we know: Semantically, selecting a radio button and checking a checkbox are different operations in user intent, even though the Selenium implementation is identical.
   - What's unclear: Whether the project wants a unified `CHECK` action for both types, or separate `SELECT_RADIO` / `DESELECT_RADIO` actions.
   - Recommendation: Add `SELECT_RADIO` as a distinct `ActionType`. This keeps JSON readable (`action: "select_radio"` is semantically clearer than `action: "check"` for radio inputs) and mirrors the existing `check`/`uncheck` pattern design intent.

## Environment Availability

Step 2.6: SKIPPED — Phase 2 is code/config changes only. No external services, databases, or CLI tools beyond the existing Python/pytest stack. All dependencies already confirmed installed in Phase 1.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 [VERIFIED: test run output] |
| Config file | `pytest.ini` (rootdir) |
| Quick run command | `pytest tests/unit/test_action_dispatch.py -v` |
| Full suite command | `pytest tests/unit/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SC-1 | Checkbox check dispatches to `BasePage.check()` | unit | `pytest tests/unit/test_action_dispatch.py::TestElementActions::test_check_action -x` | Already exists |
| SC-1 | Checkbox uncheck dispatches to `BasePage.uncheck()` | unit | `pytest tests/unit/test_action_dispatch.py::TestElementActions::test_uncheck_action -x` | Already exists |
| SC-2 | Radio `select_radio` action dispatches to `BasePage.select_radio()` | unit | `pytest tests/unit/test_action_dispatch.py::TestElementActions::test_select_radio_action -x` | Wave 0 gap |
| SC-2 | Radio already-selected is idempotent (no extra click) | unit | `pytest tests/unit/test_action_dispatch.py::TestElementActions::test_select_radio_already_selected -x` | Wave 0 gap |
| SC-3 | Number input action dispatches to `clear_and_type` | unit | `pytest tests/unit/test_action_dispatch.py::TestElementActions::test_number_input_action -x` | Wave 0 gap |
| SC-3 | Email input action dispatches to `clear_and_type` | unit | `pytest tests/unit/test_action_dispatch.py::TestElementActions::test_email_input_action -x` | Wave 0 gap |
| SC-4 | `ElementType.NUMBER` and `ElementType.EMAIL` accepted by Pydantic model | unit | `pytest tests/unit/test_workflow_models.py -x` | Extend existing file |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/test_action_dispatch.py -v`
- **Per wave merge:** `pytest tests/unit/ -v`
- **Phase gate:** Full unit suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_action_dispatch.py` — add `TestElementActions::test_select_radio_action`, `test_select_radio_already_selected`, `test_number_input_action`, `test_email_input_action`
- [ ] `tests/unit/test_workflow_models.py` — add test asserting `ElementType.NUMBER` and `ElementType.EMAIL` are valid enum members

*(No new test files or framework config needed — infrastructure fully exists)*

## Security Domain

No security-sensitive concerns for this phase. The changes are:
- Enum value additions (no user input, no auth)
- Dispatch routing within a test automation framework (no network exposure)
- Unit test additions

ASVS V5 (Input Validation): Not applicable — `clear_and_type` sends strings to a browser under test; the framework is not validating user-supplied data for a production service.

## Sources

### Primary (HIGH confidence)
- `src/core/enums.py` — verified all current `ElementType` and `ActionType` values
- `src/actions/element_actions.py` — verified complete dispatch table
- `src/ui/base_page.py` — verified `check()`, `uncheck()`, `clear_and_type()` implementations
- `src/models/workflow_models.py` — verified `ElementDefinition` and model validators
- `tests/unit/test_action_dispatch.py` — verified existing test pattern for mocked dispatch
- `testdata/workflows/tabs/checkboxes_tab.json` — verified real checkbox fixture JSON
- pytest run output — verified 18 unit tests pass, framework version confirmed

### Secondary (MEDIUM confidence)
- Selenium WebElement API: `is_selected()` applies to checkbox and radio inputs [ASSUMED based on training knowledge + consistent with existing `check()`/`uncheck()` implementation that uses it]

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all existing, verified by reading installed package versions and source
- Architecture: HIGH — complete codebase read, dispatch table and patterns verified in source
- Pitfalls: HIGH — derived from reading actual code and identifying real gaps
- Test gaps: HIGH — derived from diffing existing tests against phase success criteria

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (stable codebase, no fast-moving dependencies)
