---
status: partial
phase: 15-add-per-file-coverage-source-drilldown
source: [15-VERIFICATION.md]
started: 2026-05-31T00:52:00Z
updated: 2026-05-31T00:52:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Custom Index HTML visual rendering
expected: After running pytest with coverage, `reports/coverage/custom_index.html` renders correctly in browser — CSS styling applied, package sections collapsible via `<details open>`, 6-column table (File, Stmts, Miss, Branch, BrPart, Cover%), file links open per-file coverage pages
result: [pending]

### 2. Coverage link in HTML test report
expected: After running pytest with coverage, opening the generated `reports/run_report_*.html` shows a "Coverage Report" link in the extras section of each test row (link points to `coverage/index.html`, opens in new tab)
result: [pending]

### 3. Per-file branch highlighting
expected: Opening a per-file coverage page (e.g., `reports/coverage/src_utils_coverage_index_py.html`) shows yellow highlighting for partial-branch lines, red for uncovered lines — standard coverage.py visual rendering
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
