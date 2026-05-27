# Phase 8: Support Checkbox Search by Name+Value - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable `CHECK` and `UNCHECK` actions to locate a specific checkbox by its HTML `value` attribute when multiple `<input type="checkbox">` elements share the same `name` attribute. When `locator.by == "name"` and `element.value` is non-empty, the framework builds a targeted CSS selector and interacts with that exact checkbox.

</domain>

<decisions>
## Implementation Decisions

### Action Type Approach
- **D-01:** Reuse existing `CHECK` and `UNCHECK` action types — no new enum values. Value-based disambiguation is a transparent enhancement: when `locator.by == "name"` and `element.value` is non-empty, auto-build the CSS selector `input[type="checkbox"][name="..."][value="..."]` before locating. This mirrors the `select_radio` pattern exactly.
- **D-02:** No changes to `ActionType` enum — zero new surface area.

### BasePage Method Signature
- **D-03:** Update `BasePage.check()` and `BasePage.uncheck()` to accept an optional `value` parameter (mirrors `select_radio` signature). When `value` is set and `locator.by == "name"`, build the CSS selector inside the method, same as `select_radio` does.
- **D-04:** `ElementActions.execute()` passes `value` to `check()`/`uncheck()`, sourced from the resolved `value` argument (same pipeline as `select_radio`).

### Locator Disambiguation Trigger
- **D-05:** Same rule as `select_radio`: disambiguation activates when BOTH conditions are true — `locator.by == "name"` AND `value` is non-empty. Any other combination falls through to the plain locator path.

### Edge Cases and Error Behavior
- **D-06:** When the built CSS selector finds no element, `wait_for_visible` will timeout and raise a `TimeoutException` that propagates as `ElementActionError`. Fail loudly — consistent with all other locator failures.
- **D-07:** When `element.value` is `None` or empty string and `locator.by == "name"`, fall back to the plain locator (existing behavior). Fully backwards-compatible — existing workflows using `CHECK`/`UNCHECK` without a value continue working unchanged.

### Claude's Discretion
- CSS selector format: `input[type="checkbox"][name="{name}"][value="{value}"]` — same pattern as `select_radio` uses for radio buttons.
- Unit test coverage should include: value-present path (CSS selector built), value-absent path (plain locator used), already-checked idempotency, already-unchecked idempotency.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Analogous Implementation
- `src/ui/base_page.py` — `select_radio()` method (lines 270–286): exact pattern to replicate for checkboxes. `check()` and `uncheck()` (lines 258–268) are the methods to extend.
- `src/actions/element_actions.py` — `CHECK` and `UNCHECK` dispatch branches (lines 67–71): where `value` must be passed through to the updated `BasePage` methods.
- `src/core/enums.py` — `ActionType` enum: no changes needed.
- `src/models/workflow_models.py` — `ElementDefinition`: `value` field already exists; no schema change needed.

### Prior Phase Context
- `src/ui/base_page.py` `select_radio()` — Phase 2 decision: value+name disambiguation via CSS selector is the established pattern.

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BasePage.select_radio()` (`src/ui/base_page.py:270`): Template for the new check/uncheck value-match logic. Copy the pattern: if `value and locator.by == "name"`, build CSS `LocatorDefinition`, else use plain locator.
- `BasePage.check()` / `BasePage.uncheck()` (`src/ui/base_page.py:258–268`): Current implementations take `locator` + `name` only. Add optional `value: str = ""` parameter.

### Established Patterns
- CSS selector disambiguator: `LocatorDefinition(by="css_selector", value=f'input[type="checkbox"][name="{locator.value}"][value="{value}"]')` — same shape as the radio selector.
- Value passthrough in `ElementActions.execute()`: `str(value) if value is not None else ""` — already done for `select_radio` at line 75.

### Integration Points
- `ElementActions.execute()` CHECK branch (line 67–68): change from `self._page.check(element.locator, element.name)` to `self._page.check(element.locator, element.name, str(value) if value is not None else "")`.
- Same change for UNCHECK branch (lines 70–71).

</code_context>

<specifics>
## Specific Ideas

- The user's mental model: "same as radio but for checkboxes" — the implementation should be structurally identical to `select_radio`, just swapping `type="radio"` for `type="checkbox"` and splitting into two methods (check/uncheck) instead of one.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-support-checkbox-search-by-name-value*
*Context gathered: 2026-05-26*
