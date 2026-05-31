# Project: UI Workflow Automation

## What This Is

A data-driven Selenium browser automation framework for Python 3.9.13. Workflow authors define browser interactions as JSON files — no Python code required per workflow. The framework reads JSON definitions and executes a hierarchy of Workflow → Tabs → Pages → Sections → Elements against a live browser.

## Core Value

**Zero Python per new workflow** — write JSON, run the framework, automate the browser.

## Current State

**v1.1 Observability & Reporting milestone complete** on 2026-05-30. All 14 phases done.

- 14 phases complete, 324 unit tests passing
- Full element type coverage: checkbox, radio, select, number, email, JS execution
- Dynamic placeholder system: SIN, names, last-day-of-month, env config values
- Workflow composition: `$ref` file references + parameters + conditional `$ref` for branch workflows
- Execution control: wait_seconds, skip_if_not_visible, execute_js_script
- Video capture: ffmpeg-based screen recording in smoke tests (delete on pass, retain on fail)
- HTML test report: per-test results with step tables and screenshot links saved to `reports/`
- Coverage reporting: pytest-cov wired via `pytest.ini` addopts — terminal table + HTML at `reports/coverage/`

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
*Last updated: 2026-05-30 after v1.1 milestone*
