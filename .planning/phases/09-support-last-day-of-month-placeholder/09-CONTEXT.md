# Phase 9: Support last-day-of-month placeholder - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `${last_day_of_month}` placeholder to the existing `PLACEHOLDER_REGISTRY` in `value_resolver.py`. When resolved, it returns the last calendar date of the current month formatted as `MM/DD/YYYY`. No schema changes, no new action types — this is a pure registry extension following the Phase 4 pattern.

</domain>

<decisions>
## Implementation Decisions

### Token Name
- **D-01:** Token name is `last_day_of_month` — matches the verbose, descriptive style of existing tokens (`first_name`, `last_name`, `sin_number`, `random_number`)
- **D-02:** Used as `${last_day_of_month}` in workflow JSON `value` fields

### Format
- **D-03:** Output format is `MM/DD/YYYY` — hardcoded for this token (e.g. `05/31/2026`)
- **D-04:** The architecture uses separate token names per format (not format params), enabling future additions like `${last_day_of_month_iso}` for YYYY-MM-DD without changing the zero-arg generator pattern. Only `last_day_of_month` (MM/DD/YYYY) is in scope for this phase.

### Implementation Approach
- **D-05:** Follow the exact Phase 4 pattern: define a zero-arg generator function above the registry, then add the entry to `PLACEHOLDER_REGISTRY`
- **D-06:** Use Python `calendar.monthrange()` to compute the last day (handles all months including leap-year February correctly)
- **D-07:** Format with `datetime.strftime("%m/%d/%Y")` or equivalent zero-padded string formatting

### Claude's Discretion
- Exact function name (e.g. `generate_last_day_of_month`) — follow existing naming convention
- Import organization (add `calendar` and/or `datetime` at top of `value_resolver.py`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Implementation
- `src/actions/value_resolver.py` — Contains `PLACEHOLDER_REGISTRY`, `resolve_dynamic_value()`, and all existing generator functions. New generator and registry entry go here.

### Prior Phase Context
- `CLAUDE.md` — Project conventions including no `time.sleep()`, explicit waits, test organization

### No External Specs
No external specs, ADRs, or design documents — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PLACEHOLDER_REGISTRY: Dict[str, Callable[[], str]]` in `value_resolver.py` — direct extension point; add `"last_day_of_month": generate_last_day_of_month`
- `resolve_dynamic_value()` — already handles token lookup and `ValueError` for unknown keys; no changes needed
- `_PLACEHOLDER_PATTERN = re.compile(r"^\$\{([^}]+)\}$")` — existing regex already matches the new token

### Established Patterns
- All generators are zero-arg callables returning `str`
- Generator functions are defined **above** `PLACEHOLDER_REGISTRY` (not inline lambdas) — keep this order
- Unit tests in `tests/unit/` cover each placeholder via `resolve_dynamic_value()` — same test pattern applies

### Integration Points
- `value_resolver.py:PLACEHOLDER_REGISTRY` — sole change point for new placeholder
- `tests/unit/test_value_resolver.py` (or similar) — test coverage for the new generator

</code_context>

<specifics>
## Specific Ideas

- The token `${last_day_of_month}` is intended for form fields expecting a date input (e.g. expiry date, end date pickers)
- Example: a workflow JSON element with `"value": "${last_day_of_month}"` will receive `"05/31/2026"` when run in May 2026

</specifics>

<deferred>
## Deferred Ideas

- `${last_day_of_month_iso}` (YYYY-MM-DD format) — architecture supports it via separate token, not in this phase
- `${first_day_of_month}` — logical companion, noted for a future date-utilities phase
- `${today}` / `${today_iso}` — common date placeholder, out of scope for this phase

</deferred>

---

*Phase: 09-support-last-day-of-month-placeholder*
*Context gathered: 2026-05-29*
