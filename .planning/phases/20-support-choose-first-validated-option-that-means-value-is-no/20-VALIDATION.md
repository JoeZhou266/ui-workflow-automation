---
phase: 20
slug: support-choose-first-validated-option-that-means-value-is-no
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-07
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed; 394 tests currently passing) |
| **Config file** | `pytest.ini` |
| **Quick run command** | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py -x` |
| **Full suite command** | `.venv/bin/pytest tests/unit/ -v` |
| **Estimated runtime** | ~5 seconds (unit only, no browser) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py -x`
- **After every plan wave:** Run `.venv/bin/pytest tests/unit/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | FV-01 | — | N/A | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_selects_first_non_empty_value_option -x` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 1 | FV-02 | — | N/A | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_sentinel_case_insensitive -x` | ❌ W0 | ⬜ pending |
| 20-01-03 | 01 | 1 | FV-03 | — | N/A | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_whitespace_value_skipped -x` | ❌ W0 | ⬜ pending |
| 20-01-04 | 01 | 1 | FV-04 | — | N/A | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_empty_string_value_skipped -x` | ❌ W0 | ⬜ pending |
| 20-01-05 | 01 | 1 | FV-05 | — | N/A | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_none_value_attribute_skipped -x` | ❌ W0 | ⬜ pending |
| 20-01-06 | 01 | 1 | FV-06 | — | Raises `ElementActionError` so step records FAILED (no silent skip) | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_no_valid_option_raises -x` | ❌ W0 | ⬜ pending |
| 20-01-07 | 01 | 1 | FV-07 | — | Numeric index path unchanged (regression guard) | unit | `.venv/bin/pytest tests/unit/test_action_dispatch.py::TestElementActions::test_select_by_index -x` | ✅ exists | ⬜ pending |
| 20-01-08 | 01 | 1 | FV-08 | — | N/A | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_dispatch_passes_sentinel_to_select_dropdown -x` | ❌ W0 | ⬜ pending |
| 20-01-09 | 01 | 1 | FV-09 | — | N/A | unit | `.venv/bin/pytest tests/unit/test_base_page_select_first_valid.py::TestSelectFirstValid::test_first_valid_in_dom_order -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_base_page_select_first_valid.py` — covers FV-01..FV-06, FV-08, FV-09 (Selenium `Select`/`WebElement` mocked; no browser)

*FV-07 is already covered by `tests/unit/test_action_dispatch.py::TestElementActions::test_select_by_index`. No new framework config or fixtures needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end `first_valid` selection against a real `<select>` with a leading placeholder option | FV-01 | Requires a live browser + page; covered by unit mocks for logic but optional smoke confirmation | Author a smoke workflow JSON with `{type: select, action: select_by_index, value: "first_valid"}` and run `pytest tests/smoke/ -v` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
