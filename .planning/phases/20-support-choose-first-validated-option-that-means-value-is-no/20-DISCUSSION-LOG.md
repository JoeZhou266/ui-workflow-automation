# Phase 20: Support choose first validated option for select_by_index - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-07
**Phase:** 20-support-choose-first-validated-option-that-means-value-is-no
**Areas discussed:** Trigger mechanism, Validation rule, No-match behavior, Sentinel keyword, Whitespace handling

---

## Trigger mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Sentinel string value | Keyword in the value field; numeric values keep working unchanged | ✓ |
| Empty/omitted value | Empty/omitted value on select_by_index means 'pick first valid' | |
| Negative index (-1) | value: "-1" means 'first valid' | |

**User's choice:** Sentinel string value
**Notes:** Keeps existing numeric `select_by_index` untouched; behavior is opt-in via an explicit keyword.

---

## Validation rule

| Option | Description | Selected |
|--------|-------------|----------|
| Non-empty value attr only | First option whose value attribute is not empty/whitespace | ✓ |
| Non-empty value AND enabled | Also skip disabled options | |
| Non-empty value AND enabled AND visible text | Also require non-empty visible text | |

**User's choice:** Non-empty value attr only
**Notes:** Matches the phase title literally — only the `value` attribute's emptiness matters.

---

## No-match behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fail the step (raise error) | Raise ElementActionError → step recorded FAILED | ✓ |
| Skip gracefully (SKIPPED) | Record as SKIPPED like skip_if_not_visible | |

**User's choice:** Fail the step (raise error)
**Notes:** Consistent with existing `select_dropdown` error handling.

---

## Sentinel keyword

| Option | Description | Selected |
|--------|-------------|----------|
| first_valid | value: "first_valid" — explicit, reads clearly | ✓ |
| first_non_empty | Names the rule directly | |
| first | Shortest | |

**User's choice:** first_valid (case-insensitive match)
**Notes:** —

---

## Whitespace handling

| Option | Description | Selected |
|--------|-------------|----------|
| Treat whitespace-only as empty | Strip before checking; value="   " is skipped | ✓ |
| Only literal empty string is empty | Only value="" is skipped | |

**User's choice:** Treat whitespace-only as empty
**Notes:** Catches placeholders that use spaces as their value.

---

## Claude's Discretion

- Exact error message / log line wording.
- Detection site: `element_actions.py` vs inside `base_page.select_dropdown`.
- Helper method vs inline branch (numeric path must stay untouched).

## Deferred Ideas

None — discussion stayed within phase scope. Stricter validation variants
(skip-disabled, require-visible-text) were considered and explicitly rejected for
this phase.
