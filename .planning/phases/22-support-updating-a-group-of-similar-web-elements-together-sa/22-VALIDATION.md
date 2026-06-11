---
phase: 22
slug: support-updating-a-group-of-similar-web-elements-together-sa
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Indexed group element expansion (`index_range` + `${index}` token).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project-configured, no browser for these tests) |
| **Config file** | `pytest.ini` / `pyproject.toml` (project root) |
| **Quick run command** | `pytest tests/unit/test_workflow_models.py tests/unit/test_index_expansion.py -x` |
| **Full suite command** | `pytest tests/unit/ -v` |
| **Estimated runtime** | ~5–15 seconds (unit only, mocked driver) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/test_workflow_models.py tests/unit/test_index_expansion.py -x`
- **After every plan wave:** Run `pytest tests/unit/ -v`
- **Before `/gsd-verify-work`:** Full unit suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

Behaviors derived from CONTEXT.md decisions D-01..D-09 (no formal REQ-IDs — decisions are the requirements for this phase).

| Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|----------|-----------|-------------------|-------------|--------|
| D-01 | `index_range` field accepted on `ElementDefinition`, `None` by default | unit | `pytest tests/unit/test_workflow_models.py::TestIndexRange::test_no_index_range_defaults_to_none -x` | ❌ W0 | ⬜ pending |
| D-02a | `index_range: [0, 3]` produces indices 0,1,2,3 (four `_run_element` calls) | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_range_0_to_3_produces_four_calls -x` | ❌ W0 | ⬜ pending |
| D-02b | `start > end` raises `ValidationError` at model construction | unit | `pytest tests/unit/test_workflow_models.py::TestIndexRange::test_start_greater_than_end_raises -x` | ❌ W0 | ⬜ pending |
| D-02c | `index_range` length ≠ 2 raises `ValidationError` | unit | `pytest tests/unit/test_workflow_models.py::TestIndexRange::test_length_not_2_raises -x` | ❌ W0 | ⬜ pending |
| D-03 | `${index}` substituted embedded mid-string in `locator.value` | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_embedded_index_in_locator_value -x` | ❌ W0 | ⬜ pending |
| D-03b | `${index}` substituted in XPath locator value | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_xpath_locator_with_index -x` | ❌ W0 | ⬜ pending |
| D-04 | `${index}` substituted in element `name` → StepResult shows concrete name | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_step_result_shows_concrete_name -x` | ❌ W0 | ⬜ pending |
| D-05 | Same `value` applied to all iterations | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_same_value_all_indices -x` | ❌ W0 | ⬜ pending |
| D-07 | N StepResults recorded for N indices | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_n_results_for_n_indices -x` | ❌ W0 | ⬜ pending |
| D-08 | Failed index does not stop remaining indices in group | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_failed_index_does_not_stop_group -x` | ❌ W0 | ⬜ pending |
| D-09 | Missing index + `skip_if_not_visible=True` → SKIPPED (not FAILED) | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_missing_index_skipped_when_skip_flag -x` | ❌ W0 | ⬜ pending |
| D-09b | Missing index without skip flag → FAILED, group continues | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_missing_index_failed_without_skip_flag -x` | ❌ W0 | ⬜ pending |
| reserved | Workflow param named `index` raises `WorkflowValidationError` at load | unit | `pytest tests/unit/test_json_loader.py::TestReservedParamName::test_index_param_raises -x` | ❌ W0 | ⬜ pending |
| no-regression | Non-indexed element in same section behaves exactly as before | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_non_indexed_element_unchanged -x` | ❌ W0 | ⬜ pending |
| no-regression | Existing dispatch tests pass (`params_override=None` backward compat) | unit | `pytest tests/unit/test_action_dispatch.py -x` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_index_expansion.py` (new) — engine-level expansion: D-02a, D-03, D-03b, D-04, D-05, D-07, D-08, D-09, D-09b, no-regression. Mock `ActionFactory.run` / `WaitManager`; use a real `ResultCollector`; assert on `collector.summary().steps` names + statuses.
- [ ] `tests/unit/test_workflow_models.py::TestIndexRange` (new class) — Pydantic validation: D-01, D-02b, D-02c. Follow existing `TestElementDefinition` pattern.
- [ ] `tests/unit/test_json_loader.py::TestReservedParamName` (new class) — reserved `index` param enforcement at load.

*Existing `test_action_dispatch.py` covers the `skip_if_not_visible` path — no Wave 0 gap there.*

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Real-browser group fill against live indexed inputs (`amount_0..amount_3`) | D-03/D-04 | Requires a live AJAX page with the indexed elements | Author a sample workflow JSON with `index_range: [0,3]` and run a smoke test against a fixture page; confirm one result row per index |

*Unit coverage proves the expansion/substitution logic; the smoke test is optional confirmation, not a phase gate.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (3 new test targets)
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter (set by executor after Wave 0)

**Approval:** pending
