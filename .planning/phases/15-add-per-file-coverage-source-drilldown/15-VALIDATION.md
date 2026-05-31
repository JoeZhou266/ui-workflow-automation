---
phase: 15
slug: add-per-file-coverage-source-drilldown
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-31
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest tests/unit/test_coverage_index.py tests/unit/test_coverage_conftest.py -v --no-cov` |
| **Full suite command** | `pytest tests/unit/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/test_coverage_index.py tests/unit/test_coverage_conftest.py -v --no-cov`
- **After every plan wave:** Run `pytest tests/unit/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | COV-01 | — | N/A | unit | `pytest tests/unit/test_coverage_index.py::TestCoverageRc -v --no-cov` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | COV-02 | — | N/A | unit | `pytest tests/unit/test_coverage_index.py::TestBuildCustomIndex -v --no-cov` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | COV-03 | — | N/A | unit | `pytest tests/unit/test_coverage_index.py::TestPackageGrouping -v --no-cov` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 1 | COV-04 | — | N/A | unit | `pytest tests/unit/test_coverage_index.py::TestCssDiscovery -v --no-cov` | ❌ W0 | ⬜ pending |
| 15-01-05 | 01 | 1 | COV-05 | — | N/A | unit | `pytest tests/unit/test_coverage_index.py::TestHtmlStructure -v --no-cov` | ❌ W0 | ⬜ pending |
| 15-01-06 | 01 | 1 | COV-06 | — | N/A | unit | `pytest tests/unit/test_coverage_index.py::TestHtmlStructure -v --no-cov` | ❌ W0 | ⬜ pending |
| 15-01-07 | 01 | 1 | COV-10 | — | N/A | unit | `pytest tests/unit/test_coverage_index.py::TestMissingCoverageFile -v --no-cov` | ❌ W0 | ⬜ pending |
| 15-01-08 | 01 | 1 | COV-11 | — | N/A | unit | `pytest tests/unit/test_coverage_index.py::TestCssDiscovery -v --no-cov` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 2 | COV-07 | — | N/A | unit | `pytest tests/unit/test_coverage_conftest.py::TestSessionFinishHook -v --no-cov` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 2 | COV-08 | — | N/A | unit | `pytest tests/unit/test_coverage_conftest.py::TestNoCovDetection -v --no-cov` | ❌ W0 | ⬜ pending |
| 15-02-03 | 02 | 2 | COV-09 | — | N/A | unit | `pytest tests/unit/test_coverage_conftest.py::TestCoverageLinkExtras -v --no-cov` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_coverage_index.py` — stubs for COV-01 through COV-06, COV-10, COV-11
- [ ] `tests/unit/test_coverage_conftest.py` — stubs for COV-07, COV-08, COV-09
- [ ] `src/utils/coverage_index.py` — implementation file (created as part of Wave 0 so tests can import it)

*Existing test infrastructure (pytest.ini, conftest.py) covers all other unit tests — no framework changes needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `z_*.html` per-file pages show yellow partial branches | D-02 | Requires browser render; coverage.py handles this without code changes | Run `pytest`, open `reports/coverage/` per-file page, verify yellow highlight on uncovered branches |
| Coverage link appears in pytest HTML report extras | D-08/D-09 | Requires prior run to have generated `reports/coverage/index.html` | Run `pytest` twice; open `reports/*.html`, verify "Coverage Report" link in test row extras |
| `custom_index.html` visually consistent with coverage.py pages | D-06 | CSS rendering requires browser inspection | Open `reports/coverage/custom_index.html`, verify `style_cb_*.css` link applied |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
