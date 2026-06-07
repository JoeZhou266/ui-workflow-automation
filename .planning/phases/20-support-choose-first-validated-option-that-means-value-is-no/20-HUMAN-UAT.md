---
status: partial
phase: 20-support-choose-first-validated-option-that-means-value-is-no
source: [20-VERIFICATION.md]
started: 2026-06-07T18:38:40Z
updated: 2026-06-07T18:38:40Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end first_valid selection against a live browser
expected: Author a smoke workflow JSON with a `type: select`, `action: select_by_index`, `value: "first_valid"` element targeting a real `<select>` that has a leading placeholder option (`value=""`). Run `pytest tests/smoke/ -v`. The framework skips the placeholder and selects the first `<option>` with a non-empty `value` attribute; the step records as PASSED (not an `ElementActionError`).
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
