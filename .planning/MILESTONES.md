# Milestones

## v1.0 — Foundation Framework

**Shipped:** 2026-05-30
**Phases:** 1–11 (11 phases, 13 plans)
**Timeline:** 2026-03-31 → 2026-05-30 (60 days)
**LOC:** ~5,798 Python

### Delivered

Complete data-driven Selenium workflow automation framework — zero Python required per new workflow. Authors define browser interactions in JSON; the framework executes them across a Workflow → Tabs → Pages → Sections → Elements hierarchy.

### Key Accomplishments

1. **$ref file-reference resolution** — shared tabs/pages/sections composable across workflows with circular-ref detection
2. **Full element type coverage** — checkbox, radio, number, email, select; plus window/tab switching
3. **Registry-based placeholder expansion** — `${sin_number}`, `${first_name}`, `${last_name}`, `${last_day_of_month}` at action-dispatch time
4. **Environment config placeholder** — `${env:KEY}` resolves from YAML config; credentials never hardcoded in workflow JSON
5. **Workflow parameters + conditional $ref** — load-time `${param} == 'value'` / `!=` conditions silently omit false branches
6. **Execution control** — `wait_seconds` for timing, `execute_js_script` for arbitrary JS, `skip_if_not_visible` for graceful optional elements

### Stats

| Metric | Value |
|--------|-------|
| Phases | 11 |
| Plans | 13 |
| Unit tests | 226 |
| Python LOC | ~5,798 |
| Files changed | 117 |
| Timeline | 60 days |

### Known Deferred Items (2)

Phase 3 browser tests deferred to v1.1 — require live ChromeDriver execution (see STATE.md Deferred Items).

### Archive

- Roadmap: `.planning/milestones/v1.0-ROADMAP.md`
