# Phase 7: Support skip-if-not-visible - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-26
**Phase:** 07-support-skip-if-not-visible
**Areas discussed:** Option placement

---

## Option placement

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level field | Typed `skip_if_not_visible: bool = False` on `ElementDefinition`. Mirrors `retryable`/`retry_count`. IDE-visible, Pydantic-validated. | |
| options dict | `element.options.get("skip_if_not_visible")`. No model change. Consistent with `trigger_change_event` precedent. | ✓ |
| You decide | Claude picks the approach. | |

**User's choice:** `options` dict

**Notes:** User favored the existing `options` dict pattern for consistency with `trigger_change_event`. Key name confirmed as `"skip_if_not_visible"`.

---

## Claude's Discretion

- **Visibility probe timeout** — Zero seconds (instant check, no wait cost)
- **Skip signal mechanism** — New `SkipElementSignal` exception; engine catches it and records SKIPPED
- **pre_wait interaction** — Visibility check runs before pre_wait; not-visible → skip immediately

## Deferred Ideas

None.
