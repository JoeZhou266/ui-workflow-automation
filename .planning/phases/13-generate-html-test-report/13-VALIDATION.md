---
phase: 13
slug: generate-html-test-report
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-30
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest tests/unit/ -v` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/ -v`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | — | — | N/A | unit | `pytest tests/unit/test_html_report.py -v` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | — | — | N/A | unit | `pytest tests/unit/ -v` | ✅ | ⬜ pending |
| 13-02-01 | 02 | 2 | — | — | N/A | integration | `pytest tests/ -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_html_report.py` — stubs for HTMLReportPlugin and report generation logic
- [ ] `tests/conftest.py` — shared fixtures (already exists, will be extended)

*Existing test infrastructure covers the framework; Wave 0 only needs the new test file.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HTML report opens correctly in browser | D-01, D-02 | Requires visual inspection of rendered HTML | After `pytest`, open latest `reports/*_report_*.html` in browser; verify summary table and expandable step drill-down render |
| Screenshot thumbnails link correctly | D-05 | Relative path resolution requires browser context | Run test that fails with screenshot; verify thumbnail renders and links to `reports/screenshots/` |
| Video link renders on failed test row | D-06 | Requires live video capture integration | Run test that produces a video; verify `▶ Video` link appears in report row |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
