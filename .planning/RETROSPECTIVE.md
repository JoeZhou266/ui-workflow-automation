# Retrospective

## Milestone: v1.0 — Foundation Framework

**Shipped:** 2026-05-30
**Phases:** 11 | **Plans:** 13

### What Was Built

1. `$ref` recursive file-reference resolver with circular-ref detection — composable workflow JSON
2. Full element type coverage: checkbox, radio, number, email, window/tab switching
3. Registry-based `${placeholder}` expansion at action-dispatch time (SIN, names, dates)
4. `${env:KEY}` YAML config placeholder — credentials externalized from workflow JSON
5. `wait_seconds`, `execute_js_script`, `skip_if_not_visible` execution control primitives
6. Workflow parameters + conditional `$ref` — load-time branch selection for workflow composition

### What Worked

- **TDD discipline:** Most phases used RED-then-GREEN commit patterns; this kept tests meaningful and prevented implementation drift from spec
- **Incremental extension pattern:** Each phase added exactly one capability with no cross-phase regression (226 tests, zero regressions across all 11 phases)
- **Isolated modules:** Keeping `condition_evaluator.py` separate from `json_loader.py` made Phase 11 easy to review, test, and reason about
- **Exception wrapping at boundaries:** `WorkflowValidationError` consistently raised at the JSON-load boundary — clean error messages for workflow authors
- **Phase context files (CONTEXT.md):** Gray-area decisions captured before planning prevented mid-execution direction changes

### What Was Inefficient

- **Phase 3 browser tests deferred:** The 2 pending ChromeDriver UAT scenarios were flagged at Phase 3 verification but not driven to completion. A real-browser smoke test fixture would have resolved these during the milestone
- **REQUIREMENTS.md absent:** No requirements file was maintained; the ROADMAP served dual purpose as both roadmap and requirements tracker. This made traceability manual
- **Decisions scattered across STATE.md:** Phase-specific decisions lived in the "Accumulated Context" section of STATE.md without a unified decision log. PROJECT.md now consolidates them

### Patterns Established

- `params: dict | None = None` with in-body guard — avoids mutable default argument footgun in recursive functions
- None-sentinel pattern for list filtering — return `None` from conditional branch, filter in the list comprehension
- `except WorkflowValidationError: raise` re-raise pattern — ensures typed exceptions propagate through broader `except (IOError, ValueError)` blocks
- Phase CONTEXT.md discussion files — capture gray-area decisions before planning, reference in PLAN.md interfaces

### Key Lessons

1. **Browser smoke tests need a harness:** Without a minimal fixture that spins up Chrome and loads a workflow, browser-level behaviors are always "deferred." v1.1 should add a smoke test that exercises tab switching end-to-end.
2. **Mutable defaults in recursive functions** are a silent footgun — always use `None` + in-body initialization for dict/list parameters that shouldn't be shared across calls.
3. **Plan-level code review pays off** — all 4 warnings found in Phase 11 code review were fixable in a single pass and covered real exception-handling gaps.
4. **Condition syntax choice matters early** — the strict `${param} == 'value'` regex (no eval) locked in a safe, predictable format. Expanding it later would be a breaking change.

### Cost Observations

- Sessions: ~15 (GSD phase execution sessions)
- Timeline: 60 days (2026-03-31 → 2026-05-30)
- Notable: Wave-based parallel execution with worktree isolation kept later phases fast; Phase 11 (2 plans) executed in under 10 minutes of wall-clock agent time

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 11 |
| Plans | 13 |
| Unit tests | 226 |
| Regressions | 0 |
| Code review warnings | 4 (all fixed) |
| Deferred browser tests | 2 |
| Timeline (days) | 60 |
