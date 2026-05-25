# Phase 5: Support wait_seconds in WaitConditionType - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-25
**Phase:** 05-support-wait-seconds
**Areas discussed:** Parameter field

---

## Parameter field

| Option | Description | Selected |
|--------|-------------|----------|
| New `seconds` field | Add `seconds: Optional[float]` to WaitConditionDefinition — semantically distinct from `timeout` | |
| Reuse `timeout` field | No schema change; `timeout` means "sleep this many seconds" for wait_seconds | ✓ |

**User's choice:** Reuse `timeout` field
**Notes:** Simpler — avoids a schema change. For `wait_seconds`, the `timeout` value is the sleep duration (int seconds), consistent with the existing 1–300 range constraint.

---

## Claude's Discretion

- Validation strictness when irrelevant fields are set alongside `wait_seconds` — Claude decides
- Integer-only seconds (no float precision) — follows from `timeout: int` already being int

## Deferred Ideas

None.
