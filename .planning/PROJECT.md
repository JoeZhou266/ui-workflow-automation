# Project: UI Workflow Automation

## What This Is

A data-driven Selenium browser automation framework for Python 3.9.13. Workflow authors define browser interactions as JSON files — no Python code required per workflow. The framework reads JSON definitions and executes a hierarchy of Workflow → Tabs → Pages → Sections → Elements against a live browser.

## Core Value

**Zero Python per new workflow** — write JSON, run the framework, automate the browser.

## Current State

**v1.2 Advanced Conditional Logic milestone** — Phase 22 complete (2026-06-11).

- Phase 22 complete, 435 unit tests passing
- Full element type coverage: checkbox, radio, select, number, email, JS execution
- Dynamic placeholder system: SIN, names, last-day-of-month, env config values
- Workflow composition: `$ref` file references + parameters + conditional `$ref` for branch workflows
- Compound conditions: `&&` and `||` operators in conditional `$ref` with `&&`-before-`||` precedence (Phase 16)
- Parameter expansion: `${param_name}` in element values resolved from workflow `params` block (Phase 17)
- Execution control: wait_seconds, skip_if_not_visible, execute_js_script
- Video capture: ffmpeg-based screen recording in smoke tests (delete on pass, retain on fail)
- HTML test report: per-test results with step tables and screenshot links saved to `reports/`
- Coverage reporting: pytest-cov wired + branch coverage enabled + per-file drilldown at `reports/coverage/custom_index.html`
- Log file output: optional daily-rolling `TimedRotatingFileHandler` via `LOG_FILE_PATH` env var or `log_file_path` YAML key; rotates at midnight, 30-day retention (Phase 18)
- `first_valid` sentinel: `select_by_index` with `value: "first_valid"` (case-insensitive) selects the first `<option>` with a non-empty `value` attribute, skipping leading placeholders; raises `ElementActionError` if none qualify (Phase 20)
- Parameterized locators: locator `value` supports embedded `${param}` expansion (full-value or inside XPath/CSS, e.g. `//div[@id='${company_code}']`, `#row-${id}`) resolved from workflow `params` via a non-anchored path in `ActionFactory.run`; unknown tokens fail loud; element-value anchored path unchanged (Phase 21)
- Indexed element groups: one `ElementDefinition` with an `${index}` token plus inclusive `index_range: [start, end]` expands into N per-index interactions — `${index}` substituted (embedded anywhere) into `name` and `locator.value`, same value applied to each, one StepResult per index; a failed index continues the group and a missing index honors `skip_if_not_visible`; `index` is a reserved workflow param name (rejected at load) (Phase 22)

Tech stack: Python 3.9.13, Selenium, Pydantic v2, pytest, PyYAML, python-dotenv.

## Requirements

### Validated (v1.0)

- ✓ `$ref` file-reference resolution with circular-ref detection — v1.0
- ✓ Checkbox, radio, number, email element actions — v1.0
- ✓ Tab/window switching via workflow JSON — v1.0
- ✓ Registry-based `${placeholder}` expansion at action-dispatch time — v1.0
- ✓ `wait_seconds` fixed-duration pause in pre_wait/post_wait — v1.0
- ✓ `execute_js_script` action type for arbitrary browser JS — v1.0
- ✓ `skip_if_not_visible` conditional execution (SKIPPED not FAILED) — v1.0
- ✓ Checkbox search by name+value via CSS selector — v1.0
- ✓ `${last_day_of_month}` date placeholder — v1.0
- ✓ `${env:KEY}` YAML config placeholder for externalized credentials — v1.0
- ✓ Workflow parameters + conditional `$ref` for workflow composition — v1.0

### Validated (v1.1)

- ✓ Video capture via ffmpeg for smoke test sessions (`record_video` flag, `VideoManager`, `video_recorder` pytest fixture) — v1.1 Phase 12
- ✓ HTML test report with per-test step tables and screenshot links saved to `reports/` — v1.1 Phase 13
- ✓ pytest-cov coverage: terminal table + `reports/coverage/` HTML report on every `pytest` run — v1.1 Phase 14
- ✓ Per-file coverage drilldown: `build_custom_index()` generates `reports/coverage/custom_index.html` with branch columns (Branch/BrPart), package grouping, and per-file links — v1.1 Phase 15

### Validated (v1.2)

- ✓ Compound `&&` / `||` conditions in conditional `$ref` — two-pass token-split evaluator with `&&`-before-`||` precedence; all atoms evaluated before combining (fail-fast) — v1.2 Phase 16
- ✓ Parameter value expansion: `${param_name}` in element values resolved from workflow `params` block at action-dispatch time — v1.2 Phase 17
- ✓ Log file output: optional `TimedRotatingFileHandler` configured via `LOG_FILE_PATH` env var (priority) or `log_file_path` YAML key; midnight rotation, 30-day retention, UTF-8, `logs/` gitignored — v1.2 Phase 18
- ✓ Indexed element-group expansion: `${index}` token + inclusive `index_range: [start, end]` on one `ElementDefinition` expands into N per-index interactions (substituted into `name`/`locator.value`, same value each, one StepResult per index, fail-continue + `skip_if_not_visible` per index); `index` reserved as a workflow param name at load — v1.2 Phase 22

### Active (v2.0 candidates)

- [ ] Smoke tests with real browser (Phase 3 deferred UAT: window context, window vs tab type hint)
- [ ] Parallel element execution within a section
- [ ] Retry logic configuration per-element in workflow JSON

### Out of Scope

- GUI workflow editor — JSON-first approach
- Cloud browser execution — local ChromeDriver model
- Non-Selenium drivers (Playwright, Puppeteer) — Selenium is the defined constraint

## Key Decisions

| Decision | Outcome | Phase |
|----------|---------|-------|
| `$ref` is full-replacement (no sibling merging) | Simpler, unambiguous | 1 |
| Circular ref guard uses `frozenset` | Immutable, hashable, correct for recursion | 1 |
| Placeholder regex is anchored full-value-only | No partial substitution — prevents partial expansion bugs | 4 |
| `WaitConditionDefinition.timeout` reused for sleep duration | No schema change needed | 5 |
| JS execution is value-only (no element binding) | Simpler; return value silently ignored | 6 |
| `env:` namespace routes to `_ENV_CONFIG` before `PLACEHOLDER_REGISTRY` | Clear precedence, no key collision risk | 10 |
| `params: dict | None = None` in `resolve_refs` | Avoids mutable default argument footgun | 11 |
| None-sentinel pattern for conditional `$ref` | Filters false nodes without changing list structure | 11 |

## Context

- Implicit waits: 0 — all waits are explicit via `WaitManager`
- Never use `time.sleep()` directly — use `WaitConditionType.WAIT_SECONDS` through framework
- Re-locate elements rather than caching `WebElement` references across AJAX re-renders
- Environment config (base URLs, credentials) in `configs/env.*.yaml` — never hardcoded

---
*Last updated: 2026-06-11 after Phase 22 completion*
