# Phase 8: Support Checkbox Search by Name+Value - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-26
**Phase:** 08-support-checkbox-search-by-name-value
**Areas discussed:** Action type approach, Edge cases and error behavior

---

## Action Type Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Transparent enhancement | Reuse CHECK/UNCHECK; auto-build CSS selector when locator.by == "name" and value is set. Mirrors select_radio. | ✓ |
| New CHECK_BY_VALUE / UNCHECK_BY_VALUE actions | Two new ActionType enum values; explicit in JSON but adds surface area and diverges from radio precedent. | |
| You decide | Claude picks based on existing patterns. | |

**User's choice:** Transparent enhancement (Recommended)
**Notes:** Consistent with the Phase 2 radio button precedent.

---

## Edge Cases and Error Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Raise ElementActionError | Fail loudly — wait_for_visible timeout propagates as ElementActionError. | ✓ |
| Fall back to plain locator | Retry with original locator if CSS-by-name+value finds nothing. | |
| You decide | Claude picks consistent with framework. | |

**User's choice:** Raise ElementActionError (Recommended)
**Notes:** Consistent with all other locator failures in the framework.

---

## No-Value Path

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to plain locator (backwards-compatible) | When value is None/empty, use original locator — existing workflows unaffected. | ✓ |
| Require value when by == 'name' | Stricter — could break existing workflows. | |

**User's choice:** Yes, fall back to plain locator (Recommended)
**Notes:** Maintains full backwards compatibility.

---

## Claude's Discretion

- BasePage method signature: add optional `value: str = ""` parameter to `check()` and `uncheck()` (mirrors `select_radio`)
- CSS selector format follows radio pattern exactly

## Deferred Ideas

None.
