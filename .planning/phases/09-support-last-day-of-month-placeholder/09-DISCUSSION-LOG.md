# Phase 9: Support last-day-of-month placeholder - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 09-support-last-day-of-month-placeholder
**Areas discussed:** Token name, Format flexibility

---

## Token Name

| Option | Description | Selected |
|--------|-------------|----------|
| `last_day_of_month` | Descriptive and explicit — matches verbose style of existing tokens | ✓ |
| `end_of_month` | Shorter, common in financial/date domain language | |
| `month_last_date` | Noun-phrase style — less conventional for this codebase | |

**User's choice:** `last_day_of_month`
**Notes:** Consistent with `first_name`, `last_name`, `sin_number`, `random_number` naming convention.

---

## Format Flexibility

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcode MM/DD/YYYY for this token | Simple — always returns MM/DD/YYYY, matches zero-arg pattern | |
| Add separate tokens per format | e.g. `last_day_of_month` for MM/DD/YYYY and `last_day_of_month_iso` for YYYY-MM-DD | ✓ |
| You decide | Leave format approach to Claude | |

**User's choice:** Separate tokens per format (architecture), MM/DD/YYYY only (this phase scope)
**Notes:** User confirmed only `last_day_of_month` (MM/DD/YYYY) is in scope for Phase 9. The separate-tokens architecture enables future additions without changing the zero-arg pattern.

---

## Claude's Discretion

- Exact Python function name for the generator
- Import strategy for `calendar`/`datetime` modules

## Deferred Ideas

- `${last_day_of_month_iso}` — YYYY-MM-DD format variant, future phase
- `${first_day_of_month}` — logical companion placeholder, future phase
- `${today}` / `${today_iso}` — common date placeholders, future phase
