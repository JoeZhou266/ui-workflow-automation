---
phase: 11-support-workflow-parameters-conditional-ref
plan: "01"
subsystem: data-loader
tags: [python, pydantic, json-loader, workflow-parameters, conditional-ref, condition-evaluator]

# Dependency graph
requires:
  - phase: 10-support-env-placeholder
    provides: "resolve_dynamic_value() with ${env:KEY} support, _ENV_CONFIG module singleton"
provides:
  - "ParameterDefinition Pydantic model in workflow_models.py"
  - "parameters: Optional[List[ParameterDefinition]] field on WorkflowDefinition"
  - "evaluate_condition() pure function in src/data/condition_evaluator.py"
  - "resolve_refs() extended with params: dict argument threaded through recursive calls"
  - "WorkflowLoader.load() and load_raw() extract parameters and pass params to resolve_refs()"
  - "Conditional $ref: false-condition nodes silently omitted from parent lists (D-04)"
affects: [workflow-loading, json-loader, schema-validation, ref-resolution]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "params: dict threaded through resolve_refs() recursive calls for condition evaluation"
    - "None sentinel return from $ref branch + list filter for silent omission (D-04)"
    - "evaluate_condition() isolated pure function module — strict regex, no eval()"
    - "Parameter values resolved via resolve_dynamic_value before condition eval (D-07)"

key-files:
  created:
    - "src/data/condition_evaluator.py"
  modified:
    - "src/models/workflow_models.py"
    - "src/data/json_loader.py"

key-decisions:
  - "D-04: False-condition $ref nodes return None sentinel; list branch filters — silently omits from parent list"
  - "D-06: String-only comparisons in conditions — no type coercion"
  - "D-07: Parameter values with ${env:KEY} resolved via resolve_dynamic_value at load time before condition eval"
  - "T-11-02: evaluate_condition uses strict regex _CONDITION_PATTERN — no eval() or exec()"
  - "params: dict = {} default is safe — resolve_refs never mutates params"

# Metrics
duration: 20min
completed: 2026-05-30
---

# Phase 11 Plan 01: Support Workflow Parameters + Conditional $ref Summary

**ParameterDefinition model + evaluate_condition() pure function + resolve_refs() params threading for load-time conditional $ref resolution with silent omission of false-condition nodes**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-29T23:38:00Z
- **Completed:** 2026-05-30T03:40:00Z
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Added `ParameterDefinition` Pydantic model (`name: str`, `value: str`) above `WorkflowDefinition` in `workflow_models.py`
- Added `parameters: Optional[List[ParameterDefinition]] = None` field to `WorkflowDefinition` (backwards compatible: absent key yields `None`)
- Created `src/data/condition_evaluator.py` with `evaluate_condition(condition, params, path)` pure function supporting `==` and `!=` string operators; raises `WorkflowValidationError` for undefined params and malformed conditions; uses strict regex — no `eval()` or `exec()`
- Extended `resolve_refs()` with `params: dict = {}` argument threaded through all recursive call sites
- Added condition sibling key evaluation in `$ref` branch: false condition returns `None` sentinel
- List branch now filters `None` sentinels: `[item for item in resolved if item is not None]` — silently omits false-condition nodes (D-04)
- `WorkflowLoader.load()` extracts `parameters` from raw JSON before `$ref` resolution, resolves `${env:KEY}` values via `resolve_dynamic_value`, builds `params` dict, passes to `resolve_refs()`
- `WorkflowLoader.load_raw()` updated with same parameter extraction pattern
- `WorkflowValidationError` from `evaluate_condition` propagates cleanly (added `except WorkflowValidationError: raise` clause so it is not swallowed)
- All 212 existing unit tests pass with zero regressions (54 from workflow_models, 17 from json_loader, rest unchanged)

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add ParameterDefinition model and parameters field | 769b468 | src/models/workflow_models.py |
| 2 | Create condition_evaluator.py with evaluate_condition() | 8c6e63d | src/data/condition_evaluator.py |
| 3 | Extend resolve_refs() and WorkflowLoader with params | cc589dc | src/data/json_loader.py |

## Files Created/Modified

- `src/models/workflow_models.py` — Added `ParameterDefinition` model (12 lines) and `parameters` field on `WorkflowDefinition`
- `src/data/condition_evaluator.py` — New file: pure function `evaluate_condition()` with `_CONDITION_PATTERN` regex, `==`/`!=` operator support, fail-fast undefined param detection
- `src/data/json_loader.py` — Extended `resolve_refs()` signature and body; updated `WorkflowLoader.load()` and `load_raw()` with parameter extraction

## Decisions Made

- `params: dict = {}` is safe as a default because `resolve_refs` never mutates `params` — purely reads it in `evaluate_condition`
- The `None` sentinel approach for false-condition omission avoids changing the `resolve_refs` return type contract for scalars and dicts
- `evaluate_condition` is a standalone module (`src/data/condition_evaluator.py`) rather than inline in `json_loader.py` for testability and isolation (Claude's Discretion in CONTEXT.md)
- Pre-worktree rebase from Phase 9 base onto main was required (worktree branch lacked Phase 10 `env:` support needed for D-07)

## Deviations from Plan

### Pre-execution Fix (Required Setup)

**Worktree based on Phase 9 commit, missing Phase 10 env: support**
- **Found during:** Pre-execution worktree branch check
- **Issue:** Worktree branch was created from `e927fd9` (Phase 9 state), missing Phase 10 commits (`aa982bc` etc.) that add `${env:KEY}` support to `resolve_dynamic_value()`. D-07 requires calling `resolve_dynamic_value()` on parameter values.
- **Fix:** Rebased worktree branch onto `main` — fast-forward, no conflicts, all 212 tests passed after rebase
- **Impact:** None — clean rebase

No code deviations — plan executed exactly as written.

## Known Stubs

None — all implementation is complete and functional.

## Threat Flags

No new security surface beyond the plan's threat model. T-11-02 mitigation fully implemented: `evaluate_condition` uses strict regex `_CONDITION_PATTERN` with no `eval()` or `exec()`.

## Self-Check: PASSED

- `src/models/workflow_models.py` — FOUND: class ParameterDefinition at line 139
- `src/data/condition_evaluator.py` — FOUND: created new file with evaluate_condition()
- `src/data/json_loader.py` — FOUND: params: dict at lines 20, 117, 157
- Commit 769b468 — FOUND in git log
- Commit 8c6e63d — FOUND in git log
- Commit cc589dc — FOUND in git log
- All 212 unit tests pass
