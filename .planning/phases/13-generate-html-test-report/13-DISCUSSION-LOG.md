# Phase 13: Generate HTML Test Report - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 13-generate-html-test-report
**Areas discussed:** Report scope, Library approach, Artifact embedding, Report trigger & naming

---

## Report scope

| Option | Description | Selected |
|--------|-------------|----------|
| Both levels (Recommended) | Top section: pytest test summary. Bottom: per-test expandable drill-down showing full Tab→Page→Section→Element step chain from ResultCollector. | ✓ |
| pytest test level only | Standard pytest-html output: test function names, pass/fail/skip counts, error messages. No workflow step details. | |
| Workflow step level only | Custom report showing element-level execution chain only. No standard pytest test names visible. | |

**User's choice:** Both levels (Recommended)
**Notes:** Wants both pytest-level summary and the full workflow step hierarchy visible per test.

---

| Option | Description | Selected |
|--------|-------------|----------|
| All steps with status (Recommended) | Every element step — PASSED/FAILED/SKIPPED — with Tab→Page→Section→Element hierarchy, action, duration_ms. On failure: error_message and failure_phase. | ✓ |
| Failed steps only | Only FAILED steps in the drill-down. Passed steps counted but not listed. | |
| Summary counts only | Per-test totals/counts only — no individual step rows. | |

**User's choice:** All steps with status (Recommended)

---

## Library approach

| Option | Description | Selected |
|--------|-------------|----------|
| pytest-html + custom plugin hook (Recommended) | pytest-html 4.2.0 already installed. Extend via plugin hooks to inject per-test workflow step details. One HTML file, no extra server. | ✓ |
| Allure | Already installed. Rich UI, history, attachments. Requires allure-serve/allure generate to view — extra operational overhead. | |
| Custom Jinja2 template | Full control over layout. Adds Jinja2 as new dependency. | |

**User's choice:** pytest-html + custom plugin hook (Recommended)

---

## Artifact embedding

| Option | Description | Selected |
|--------|-------------|----------|
| Screenshots linked, videos linked (Recommended) | Screenshots as clickable thumbnails (linked path). Videos as linked filename. Both only on FAILED steps/tests. No extra deps. | ✓ |
| Screenshots embedded (base64) | Screenshots base64-encoded in HTML. Fully self-contained but large file. | |
| No media in this phase | Step results text only. Defer artifact embedding. | |

**User's choice:** Screenshots linked, videos linked (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Relative paths (Recommended) | e.g. `../screenshots/...` relative to HTML file in reports/. Works when reports/ folder viewed together. | ✓ |
| Absolute paths | Full filesystem paths. Breaks if shared with another machine. | |

**User's choice:** Relative paths (Recommended)

---

## Report trigger & naming

| Option | Description | Selected |
|--------|-------------|----------|
| Always auto-generate (Recommended) | --html added to addopts in pytest.ini. Every pytest run produces a report. | ✓ |
| Explicit --report flag | Report only generated when flag is passed. | |

**User's choice:** Always auto-generate (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Single overwritten report.html | Always writes to reports/report.html. Simple, predictable. | |
| Timestamped per run | reports/<workflow_name>_report_<YYYYMMDD_HHMMSS>.html. Keeps history. | ✓ |
| Timestamped + latest symlink | Timestamped file + reports/report.html symlink. History + easy access. | |

**User's choice:** Timestamped per run — `reports/<workflow_name>_report_<YYYYMMDD_HHMMSS>.html`
**Notes:** Flat in `reports/` directory (not a subdirectory).

---

| Option | Description | Selected |
|--------|-------------|----------|
| Flat in reports/ (Recommended) | e.g. reports/sample_workflow_report_20260530_143022.html | ✓ |
| Subdirectory reports/html/ | e.g. reports/html/sample_workflow_report_20260530_143022.html | |

**User's choice:** Flat in reports/ (Recommended)

---

## Claude's Discretion

- Exact pytest-html 4.x hook API names (researcher to verify)
- How ResultCollector instance is passed to conftest hook (stash vs fixture vs module-level)
- HTML structure for step drill-down (collapsible details/summary)
- Unit test coverage for report generation logic
- .gitignore update for reports/*.html

## Deferred Ideas

- Latest symlink (reports/report.html → latest timestamped)
- Allure report for CI
- Report auto-cleanup (keep last N)
- Base64 screenshot embedding
- JSON export alongside HTML
