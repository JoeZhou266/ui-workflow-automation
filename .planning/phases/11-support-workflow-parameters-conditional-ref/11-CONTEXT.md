# Phase 11: Support Workflow Parameters + Conditional $ref — Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `parameters` block to `WorkflowDefinition` (name/value pairs) that propagates down
the hierarchy. Extend `$ref` resolution so a `condition` sibling key can be evaluated
against those parameters at load time — when the condition is false, the `$ref` node is
silently omitted from its parent list. No runtime changes; this is purely a load-time
and schema extension.

</domain>

<decisions>
## Implementation Decisions

### Parameter Declaration

- **D-01:** `parameters` is declared **only** at the `WorkflowDefinition` root. Tabs, pages,
  and sections inherit the workflow parameters read-only. No per-level parameter blocks.
  Keeps the model simple — no merge/precedence rules needed.

### Condition Syntax

- **D-02:** Condition operators for Phase 11: `==` and `!=` only.
  Format: `${param_name} == 'value'` or `${param_name} != 'value'`.
  String-quoted values on the right-hand side.

- **D-03:** If a condition references a parameter name not declared in the workflow's
  `parameters` list, `resolve_refs()` raises a `WorkflowValidationError` at load time.
  Fail fast — undefined params in conditions are authoring mistakes.

### Condition-False Behavior

- **D-04:** When a condition evaluates to `false`, the `$ref` node is **silently omitted**
  from its parent list. No log, no empty placeholder — the parent list simply has one
  fewer item.

- **D-05:** Conditional `$ref` is supported at **tabs, pages, and sections levels only**.
  Element-level `$ref` does not need condition support (Phase 7's `skip_if_not_visible`
  covers runtime conditional element execution).

### Parameter Value Types

- **D-06:** Parameter values are **strings only**. Condition comparisons are always
  string equality/inequality. No type coercion.

- **D-07:** Parameter values **may contain `${env:KEY}` placeholders** (Phase 10 pattern).
  These are resolved at load time — before condition evaluation — so parameters can be
  driven by env YAML config without hardcoding values in workflow JSON.

### JSON Schema Shape

The workflow JSON with parameters looks like:
```json
{
  "workflow_name": "...",
  "start_url": "...",
  "parameters": [
    { "name": "account_type", "value": "OPEN" }
  ],
  "tabs": [
    { "$ref": "./tabs/basic_tab.json" },
    { "$ref": "./tabs/summary_tab.json", "condition": "${account_type} == 'OPEN'" }
  ]
}
```

A `$ref` node without a `condition` key resolves as before (full replacement, no change).

### Claude's Discretion

- Where exactly to implement `evaluate_condition()` — a new `src/data/condition_evaluator.py`
  module or inline in `json_loader.py`. Keep it isolated from the main loader if it grows.
- Whether `resolve_refs()` accepts `params: dict` as a new argument (threaded through
  recursive calls) vs. using a class-based resolver. Thread-through is the simplest path.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core files to extend
- `src/data/json_loader.py` — `resolve_refs()` to extend: read `condition` sibling key,
  evaluate it, pass `params` dict through recursive calls; omit node from list when false
- `src/models/workflow_models.py` — Add new `ParameterDefinition` model (`name: str`,
  `value: str`); add `parameters: Optional[List[ParameterDefinition]]` to `WorkflowDefinition`

### Prior phase patterns to follow
- `src/utils/value_resolver.py` — Phase 4/10 `resolve_dynamic_value()` and `PLACEHOLDER_REGISTRY`;
  use `resolve_dynamic_value()` to expand `${env:KEY}` in parameter values at load time
  before condition evaluation
- `src/core/exceptions.py` — `WorkflowValidationError` for undefined-param errors at load time

### Phase decisions to carry forward
- Phase 1 decision: `$ref` is full-replacement (no sibling key merging) — Phase 11 carves
  out a single exception: `condition` is the only sibling key that is read before replacement.
  All other sibling keys remain ignored.
- Phase 10 decision: `${env:KEY}` resolves via `_ENV_CONFIG` dict wired in `AppConfig.__init__`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `resolve_dynamic_value()` in `src/utils/value_resolver.py` — already handles `${env:KEY}`
  expansion; call this on each parameter's `value` string at load time before condition eval
- `WorkflowValidationError` in `src/core/exceptions.py` — correct exception for load-time
  authoring errors (undefined params, malformed condition strings)

### Established Patterns
- `resolve_refs()` is a pure recursive function with `_resolving: frozenset` for cycle detection;
  extend by adding `params: dict = {}` parameter threaded through all recursive calls
- List resolution: `[resolve_refs(item, base_dir, _resolving) for item in data]` — change
  to filter-map: resolve each item, omit items that return a sentinel (e.g., `None`) when
  condition is false
- Pydantic v2 `model_validate()` already used in `WorkflowLoader.load()` — new
  `ParameterDefinition` model follows same pattern as `LocatorDefinition`

### Integration Points
- `WorkflowLoader.load()` in `json_loader.py` must extract `parameters` from raw JSON
  before calling `resolve_refs()`, resolve `${env:KEY}` in each value, build a `params: dict`,
  and pass it into the first `resolve_refs()` call
- Tests: `tests/unit/` — new unit test file for parameter parsing + condition evaluation

</code_context>

<specifics>
## Specific Ideas

- User-provided condition example: `{ "$ref": "./pages/summary_page.json", "condition": "${account_type} == 'OPEN'" }`
- Note: user's original example spelled "conditon" (typo) — canonical field name is `condition`
- Parameters are a flat list of `{name, value}` objects (not a plain dict) to keep JSON
  authoring consistent with the rest of the schema (array of named objects pattern)

</specifics>

<deferred>
## Deferred Ideas

- Multi-level parameters (tab/page/section-level parameter overrides) — deferred to future phase
- Operators beyond == and != (contains, in [...], and/or) — deferred to future phase
- Element-level conditional $ref — deferred (Phase 7 covers runtime element skipping)

</deferred>

---

*Phase: 11-support-workflow-parameters-conditional-ref*
*Context gathered: 2026-05-29*
