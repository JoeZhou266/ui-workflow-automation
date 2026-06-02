# Roadmap: UI Workflow Automation

## Milestones

- ✅ **v1.0 Foundation Framework** — Phases 1–11 (shipped 2026-05-30)
- ✅ **v1.1 Observability & Reporting** — Phases 12–15 (shipped 2026-05-31)
- 🚧 **v1.2 Advanced Conditional Logic** — Phases 16+ (in progress)

## Phases

<details>
<summary>✅ v1.0 Foundation Framework (Phases 1–11) — SHIPPED 2026-05-30</summary>

- [x] Phase 1: Support Nested JSON (2/2 plans) — completed 2026-05-15
- [x] Phase 2: Support More Web Elements (2/2 plans) — completed 2026-05-16
- [x] Phase 3: Support Tab Switching and New Window Focus (2/2 plans) — completed 2026-05-15
- [x] Phase 4: Support Dynamic Placeholder Expansion (1/1 plan) — completed 2026-05-25
- [x] Phase 5: Support wait_seconds in WaitConditionType (1/1 plan) — completed 2026-05-26
- [x] Phase 6: Support execute_js_script Action Type (1/1 plan) — completed 2026-05-25
- [x] Phase 7: Support skip-if-not-visible (1/1 plan) — completed 2026-05-26
- [x] Phase 8: Support checkbox search by name+value (1/1 plan) — completed 2026-05-26
- [x] Phase 9: Support last-day-of-month placeholder (1/1 plan) — completed 2026-05-29
- [x] Phase 10: Support ${env:KEY} config placeholder (1/1 plan) — completed 2026-05-30
- [x] Phase 11: Support Workflow Parameters + Conditional $ref (2/2 plans) — completed 2026-05-29

Full phase details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details open>
<summary>✅ v1.1 Observability & Reporting (Phases 12–15) — SHIPPED 2026-05-31</summary>

- [x] Phase 12: Support Video Capture for Failed Tests (3/3 plans) — completed 2026-05-30
- [x] Phase 13: Generate HTML Test Report with Results and Details (2/2 plans) — completed 2026-05-31
- [x] Phase 14: Add Python unit test coverage and report in project (1/1 plan) — completed 2026-05-30
- [x] Phase 15: Add per-file coverage source drilldown (2/2 plans) — completed 2026-05-31

Plans:
- [x] 12-01-PLAN.md — Core infrastructure: VideoManager, constants, AppConfig field, env YAML configs
- [x] 12-02-PLAN.md — Pytest integration: pytest_runtest_makereport hook + video_recorder fixture
- [x] 12-03-PLAN.md — Tests + .gitignore: unit tests for VideoManager, .gitignore update
- [x] 13-01-PLAN.md — HTML report utility: constants, html_report.py pure functions, unit tests HTML-01..09
- [x] 13-02-PLAN.md — Pytest integration: pytest_configure hook, StashKeys, workflow_report_extras, conftest unit tests HTML-10..12
- [x] 14-01-PLAN.md — Coverage config: pytest-cov dependency, pytest.ini addopts, .coveragerc, .gitignore
- [x] 15-01-PLAN.md — Branch coverage config, COVERAGE_DIR constant, build_custom_index() implementation, unit tests COV-01..06,10,11
- [x] 15-02-PLAN.md — conftest.py hooks: pytest_sessionfinish + coverage link in makereport, conftest unit tests COV-07..09

</details>

<details open>
<summary>🚧 v1.2 Advanced Conditional Logic (Phases 16+) — in progress</summary>

- [x] Phase 16: Support logical operators (&& / ||) in conditional $ref (1/1 plan) — completed 2026-05-31
- [x] Phase 17: Support using parameters defined in workflow in element values as placeholders (2/2 plans) — completed 2026-06-02

Plans:
- [x] 16-01-PLAN.md — TDD: add compound condition tests (RED) then implement two-pass token-split evaluator (GREEN); 9 new tests (OP-01..10)
- [x] 17-01-PLAN.md — TDD RED: write TestParamExpansion class with VP-01..VP-10 failing stubs in test_value_resolver.py
- [x] 17-02-PLAN.md — TDD GREEN: implement params kwarg in value_resolver.py, remove singleton in action_factory.py, wire params through workflow_engine.py

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Support Nested JSON | v1.0 | 2/2 | Complete | 2026-05-15 |
| 2. Support More Web Elements | v1.0 | 2/2 | Complete | 2026-05-16 |
| 3. Support Tab Switching and New Window Focus | v1.0 | 2/2 | Complete | 2026-05-15 |
| 4. Support Dynamic Placeholder Expansion | v1.0 | 1/1 | Complete | 2026-05-25 |
| 5. Support wait_seconds in WaitConditionType | v1.0 | 1/1 | Complete | 2026-05-26 |
| 6. Support execute_js_script Action Type | v1.0 | 1/1 | Complete | 2026-05-25 |
| 7. Support skip-if-not-visible | v1.0 | 1/1 | Complete | 2026-05-26 |
| 8. Support checkbox search by name+value | v1.0 | 1/1 | Complete | 2026-05-26 |
| 9. Support last-day-of-month placeholder | v1.0 | 1/1 | Complete | 2026-05-29 |
| 10. Support ${env:KEY} config placeholder | v1.0 | 1/1 | Complete | 2026-05-30 |
| 11. Support Workflow Parameters + Conditional $ref | v1.0 | 2/2 | Complete | 2026-05-29 |
| 12. Support Video Capture for Failed Tests | v1.1 | 3/3 | Complete   | 2026-05-30 |
| 13. Generate HTML Test Report | v1.1 | 2/2 | Complete | 2026-05-31 |
| 14. Add Python unit test coverage and report in project | v1.1 | 1/1 | Complete | 2026-05-30 |
| 15. Add per-file coverage source drilldown | v1.1 | 2/2 | Complete | 2026-05-31 |
| 16. Support logical operators (&& / \|\|) in conditional $ref | v1.2 | 1/1 | Complete | 2026-05-31 |
| 17. Support using parameters defined in workflow in element values as placeholders | v1.2 | 2/2 | Complete | 2026-06-02 |
