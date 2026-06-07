# Phase 20: Support choose first validated option (value not empty) for select_by_index - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

When an element is `type: select` and `action: select_by_index`, support a mode
that auto-selects the **first valid option** — the first `<option>` whose `value`
attribute is non-empty — instead of requiring an explicit numeric index. This lets
workflow authors skip the leading placeholder option (typically `value=""`, e.g.
"Please select…") without knowing its position.

**In scope:** A sentinel keyword recognized by the existing `select_by_index`
action that triggers first-valid selection on `<select>` elements.

**Out of scope:** Changes to `select_by_text` / `select_by_value`; multiselect
handling; any new action type or element type; "first valid by visible text"
matching (only `value`-attribute emptiness is in scope).

</domain>

<decisions>
## Implementation Decisions

### Trigger mechanism
- **D-01:** Triggered by a **sentinel string value** in the element's `value`
  field. Numeric values continue to work exactly as today (`select_by_index(int(value))`).
- **D-02:** The sentinel keyword is **`first_valid`**, matched **case-insensitively**
  (e.g. `"first_valid"`, `"First_Valid"`, `"FIRST_VALID"` all trigger the behavior).

### Validation rule (what makes an option selectable)
- **D-03:** "Validated" = the option's **`value` attribute is non-empty**. Scan
  options in DOM order and select the first one that qualifies.
- **D-04:** **Whitespace-only values count as empty** — strip the `value` attribute
  before checking, so `value="   "` is skipped just like `value=""`.
- **D-05:** Only the `value` attribute is considered. Disabled state and visible
  text are NOT part of the rule (explicitly rejected the stricter variants).

### Failure behavior
- **D-06:** If **no option** passes the validation rule (all options have empty /
  whitespace-only values), **raise `ElementActionError`** so the step is recorded
  as FAILED with a clear message. This is consistent with existing select failures
  (`select_dropdown` already raises `ElementActionError`). Not a graceful SKIP.

### Claude's Discretion
- Exact wording of the error message and log lines.
- Whether the sentinel detection lives in `element_actions.py` (before dispatch to
  `select_dropdown`) or inside `base_page.select_dropdown` — planner/executor's call.
- Whether to add a dedicated helper (e.g. `select_first_valid_option`) vs inline
  branch — as long as numeric `select_by_index` behavior is untouched.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs or ADRs — requirements fully captured in the decisions above.
ROADMAP.md Phase 20 lists no canonical refs. The relevant context is existing code
(see Existing Code Insights below).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ui/base_page.py:237` `select_dropdown(locator, by, value, name)` — the
  current select entry point. `by == "index"` branch at line 258-259 does
  `Select(el).select_by_index(int(value))`. This is where (or just upstream of)
  the sentinel must be detected. The `Select` object exposes `.options` for
  scanning option `value` attributes.
- `src/actions/element_actions.py:64-65` — `ActionType.SELECT_BY_INDEX` branch
  dispatches to `select_dropdown(..., "index", str(value), ...)`. Candidate site
  for sentinel detection before the numeric path.

### Established Patterns
- `select_dropdown` raises `ElementActionError(..., element_name=name)` on the
  unknown-`by` path — mirror this exception type/shape for the no-valid-option case.
- Selenium `Select` from `selenium.webdriver.support.ui` is already imported and
  used for option handling.
- Element values are strings at dispatch time (`str(value)`); the numeric path
  relies on `int(value)`, so sentinel detection must happen before the `int()` cast
  to avoid a `ValueError`.

### Integration Points
- `src/core/enums.py:28` defines `SELECT_BY_INDEX = "select_by_index"` — no new
  enum needed; this is a value-level convention, not a new action.

</code_context>

<specifics>
## Specific Ideas

- JSON usage shape (illustrative):
  `{ "type": "select", "action": "select_by_index", "value": "first_valid", "locator": {...} }`
- Behavior: scan `<option>` elements in DOM order, pick the first with a
  non-empty (post-strip) `value` attribute, select it. If none qualify → FAIL.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Stricter validation variants —
skip-disabled and require-visible-text — were considered and explicitly rejected
for this phase, not deferred.)

</deferred>

---

*Phase: 20-support-choose-first-validated-option-that-means-value-is-no*
*Context gathered: 2026-06-07*
