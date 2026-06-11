# Phase 22: Support updating a group of similar web elements together — Research

**Researched:** 2026-06-11
**Domain:** Python framework extension — loop expansion seam in Selenium workflow engine
**Confidence:** HIGH (all findings are from direct source inspection of the codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Group declared as a single `ElementDefinition` with `${index}` token + new `index_range` field. Framework loops, substituting index per iteration. Reuses Phase 17/21 `${param}` expansion machinery.
- **D-02:** Range syntax `index_range: [start, end]`, inclusive both ends. `[0, 3]` → indices 0, 1, 2, 3.
- **D-03:** Token `${index}` substituted **embedded anywhere** in element `name` AND `locator.value` (both mid-string and suffix). Mirrors Phase 21 partial (non-anchored) locator expansion.
- **D-04:** `${index}` substituted in the element `name` per iteration so each StepResult row shows the concrete per-index name.
- **D-05:** All indices receive the **same `value`** — same value for every loop iteration.
- **D-06:** Schema must stay open to a future per-index value list without breaking existing JSON.
- **D-07:** Record **one StepResult per index** (e.g. `amount_0` PASS, `amount_1` FAIL, `amount_2` PASS).
- **D-08:** **Continue group on failed index** — a failing index does NOT stop remaining indices.
- **D-09:** Missing index honors element's `skip_if_not_visible`; if absent and element opts in → SKIPPED; otherwise FAILED, group continues.

### Claude's Discretion
- Exact field/model name on `ElementDefinition` and Pydantic validation shape for `index_range`.
- The seam where index expansion happens: pre-`_run_element` N-element expansion vs threaded `${index}` into the existing resolution path per iteration.
- Token/regex for `${index}` and how it composes with the Phase 17 anchored value path and Phase 21 partial locator path.
- Whether `${index}` is reserved (cannot collide with a workflow `param` named `index`) and enforcement.
- Exact wording of error/log messages.

### Deferred Ideas (OUT OF SCOPE)
- Per-index distinct values (e.g. `value: ["100","200","300"]`) — schema stays open, not implemented now.
- Dynamic count discovery at runtime.
- Non-contiguous/explicit index lists and multi-dimensional indices.
</user_constraints>

---

## Summary

Phase 22 adds a loop-expansion capability to the workflow engine: one `ElementDefinition` with an `${index}` token and an `index_range: [start, end]` field expands into N per-index iterations, each recorded as its own StepResult. The implementation composes with the two existing expansion seams — Phase 17's anchored full-value element-value path (`value_resolver.py`) and Phase 21's partial/embedded locator path (`action_factory._resolve_locator`) — by injecting a loop-scoped `index` entry into the params dict on each iteration.

The critical design question is the expansion seam. Research confirms the **loop-in-`_run_section`** approach (expand in the loop body that already iterates elements, producing one `_run_element` call per index with a mutated-name copy of the element) is the cleanest seam: it preserves the entire existing `_run_element` machinery unchanged, propagates `index` as a loop-scoped param overlay, and naturally satisfies D-07 (one result per index), D-08 (continue on fail), and D-09 (per-index `SkipElementSignal`) with zero extra control flow.

Pydantic v2 (2.13.4) is installed. The `index_range` field should be `Optional[List[int]] = None` with a `@model_validator(mode="after")` that checks length == 2 and `start <= end`, consistent with the existing `value_required_for_input_actions` validator pattern in `ElementDefinition`. The `${index}` token should be treated as a reserved name in the loop-scoped params overlay, with an explicit `ValueError` at load time if a workflow parameter is named `index`.

**Primary recommendation:** Implement the expansion loop inside `_run_section`, injecting `{"index": str(i)}` as an overlay merged with `self._params` for each iteration, passing the merged dict to a temporary element copy with the concrete per-index `name` substituted. The value and locator expansion paths (Phase 17 anchored and Phase 21 partial) are already params-aware and will handle `${index}` automatically.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Index range field declaration | Model (`workflow_models.py`) | Data layer (Pydantic validation) | Field lives on `ElementDefinition`; validator enforces length-2 and start≤end at load time |
| Loop expansion — iterate indices | Workflow engine (`workflow_engine.py`) | — | `_run_section` is the only caller of `_run_element` per element; expansion wraps this call site |
| `${index}` substitution in locator.value | Action layer (`action_factory._resolve_locator`) | `value_resolver.resolve_locator_params` | Phase 21 seam already handles all `${param}` tokens embedded in locator via non-anchored regex |
| `${index}` substitution in element value | Action layer (`value_resolver.resolve_dynamic_value`) | `ValueResolver._resolve_string` | Phase 17 anchored path checks `params` dict; `index` key in params dict is enough |
| `${index}` substitution in element name | Workflow engine (`_run_section` loop body) | — | `name` is not resolved through value/locator paths; must be substituted at the engine expansion site |
| Per-index StepResult recording | Workflow engine (`_run_element`) | `ResultCollector` | `_run_element` receives the per-index concrete element; result recorded under the substituted name |
| D-09 skip-on-missing-index | Action layer (`ActionFactory.run`) | `SkipElementSignal` | Already-existing path: `skip_if_not_visible` probe raises `SkipElementSignal`; no new code needed |
| Reserved name enforcement (`${index}` ≠ param) | Data layer (`json_loader.py` or model validator) | — | Fail-loud at load time before any execution; cleanest place is model validation or loader |

---

## Standard Stack

This phase is a pure internal extension — no new external packages are required.

### Core (already installed)
| Library | Version | Purpose | Role in Phase 22 |
|---------|---------|---------|-----------------|
| pydantic | 2.13.4 [VERIFIED: pip show] | Schema validation | Add `index_range` field + `@model_validator` to `ElementDefinition` |
| pytest | (project) | Test runner | Unit tests for new behaviors |

### No New Dependencies

No new packages are installed in this phase.

---

## Package Legitimacy Audit

No new packages — audit not applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
WorkflowEngine._run_section(section, ctx)
    for each element in section.elements:
        if element.index_range is None:          ← existing path, unchanged
            _run_element(element, section, ctx.at_element(element.name))
        else:                                    ← NEW: loop expansion
            for i in range(start, end+1):
                merged_params = {**self._params, "index": str(i)}
                concrete_name = _substitute_index(element.name, i)
                concrete_elem = element.model_copy(update={"name": concrete_name})
                _run_element(concrete_elem, section, ctx.at_element(concrete_name),
                             params_override=merged_params)

WorkflowEngine._run_element(element, section, ctx, params_override=None)
    params = params_override if params_override is not None else self._params
    factory = ActionFactory(section, self._wm, params=params)
    # ... existing try/except block unchanged ...
    # SkipElementSignal, WaitTimeoutError, ElementActionError all handled as before

ActionFactory.run(element)
    resolved_locator = self._resolve_locator(element.locator)
    # _resolve_locator calls resolve_locator_params(value, self._params)
    # _LOCATOR_PARAM_PATTERN is non-anchored → matches ${index} embedded anywhere
    #
    # skip_if_not_visible probe: raises SkipElementSignal(element.name)
    # → element.name is ALREADY the concrete per-index name (e.g. "amount_2")
    #
    resolved_value = self._resolver.resolve(element.value)
    # ValueResolver._resolve_string → resolve_dynamic_value(value, params=self._params)
    # _PLACEHOLDER_PATTERN is anchored; if value == "${index}" → resolves to str(i)
    # if value is a literal like "100" → returned unchanged
```

### Recommended Project Structure
```
src/
├── models/
│   └── workflow_models.py       # Add index_range field + validator to ElementDefinition
├── workflow/
│   └── workflow_engine.py       # Add loop expansion in _run_section; add params_override to _run_element
└── (no other files change)

tests/unit/
└── test_workflow_models.py      # Add TestIndexRange class
└── test_action_dispatch.py      # Extend with ${index} in locator tests (optional)
└── test_index_expansion.py      # New: engine-level loop expansion tests (or add class to existing)
```

---

## The Expansion Seam — Detailed Analysis

### Option A: Expand before `_run_element` in `_run_section` (RECOMMENDED)

**How it works:** When `_run_section` encounters an element with `index_range`, it loops `range(start, end+1)`, builds a per-index `merged_params` dict, substitutes the `name`, creates a concrete element copy, and calls `_run_element` once per index.

**Key property:** `_run_element` is unchanged except for an optional `params_override` parameter (defaulting to `None`, which falls back to `self._params` — fully backward-compatible). The entire existing try/except block — `SkipElementSignal`, `WaitTimeoutError`, `ElementActionError`, generic `Exception` — applies identically to each per-index call.

**D-07 (one result per index):** Natural outcome — each `_run_element` call records one StepResult under the concrete per-index name.

**D-08 (continue group on fail):** Natural outcome — `_run_element` already catches all exceptions internally, records FAIL, and returns. The `_run_section` loop proceeds to the next index.

**D-09 (missing index → SKIPPED via `skip_if_not_visible`):** Natural outcome — `ActionFactory.run` raises `SkipElementSignal` if `skip_if_not_visible` is set and the element is not visible; `_run_element` catches it and records SKIP. No new code.

**Why this is cleanest:** Zero changes to `ActionFactory`, `ValueResolver`, `LocatorResolver`, or `ResultCollector`. All existing Phase 17 and Phase 21 expansion machinery is exercised unchanged — `${index}` is simply a key in the params dict.

### Option B: Thread index inside `_run_element` via a decorator or generator

This would require `_run_element` to detect `index_range` and loop internally, which breaks the single-responsibility contract (one element = one step) and complicates the result recording. Not recommended.

### Name Substitution for `element.name`

The element `name` is NOT processed by `ValueResolver` or `resolve_locator_params` — it is used directly as an identifier in `ExecutionContext.at_element(element.name)` and in log messages. Therefore `${index}` in `element.name` must be substituted at the expansion site (in `_run_section`) before passing the element to `_run_element`.

**Implementation:** A simple inline string replace is sufficient:
```python
# [VERIFIED: codebase] _LOCATOR_PARAM_PATTERN already in value_resolver.py
concrete_name = element.name.replace("${index}", str(i))
```
Alternatively, reuse `_LOCATOR_PARAM_PATTERN` (non-anchored) for consistency:
```python
from src.actions.value_resolver import _LOCATOR_PARAM_PATTERN
concrete_name = _LOCATOR_PARAM_PATTERN.sub(
    lambda m: str(i) if m.group(1) == "index" else m.group(0),
    element.name
)
```
The first form (simple `str.replace`) is adequate since `name` substitution is only for `${index}` (not arbitrary `${param}` tokens, which don't appear in `name`).

---

## `${index}` Composition with Phase 17 and Phase 21 Expansion Modes

### How Phase 17 anchored path handles `${index}` in element value

`resolve_dynamic_value(value, params)` uses `_PLACEHOLDER_PATTERN = re.compile(r"^\$\{([^}]+)\}$")` — anchored, full-value only. [VERIFIED: src/actions/value_resolver.py line 15]

If the element value is `"${index}"` (the entire string is the token), the anchored pattern matches, `key == "index"`, and the function looks up `params["index"]` = `str(i)`. This works exactly as Phase 17 param lookup works for any workflow parameter.

If the element value is `"amount_${index}"` (embedded), the anchored pattern does NOT match and the string is returned unchanged. This is correct by design — element values use full-value-only expansion (Phase 4/17 decision). An element with `value: "amount_${index}"` is an authoring error and should fail-loud via the existing `ValueError` path (the anchored match fails → `resolve_dynamic_value` returns the string as-is, no error). Actually, because anchored match fails, the function returns the raw string unchanged — it does NOT raise. This is the existing behavior for any partial token in a value (see Phase 17 D-03: "partial token not expanded"). For Phase 22, this is acceptable because the roadmap use case is: the **value is constant** (e.g. `"100"`) and the **name/locator** vary by index (D-05).

**Conclusion:** Phase 17 path requires NO changes. `${index}` as a full element value works; as a partial value it is silently passed through (consistent with existing behavior for partial tokens).

### How Phase 21 partial path handles `${index}` in `locator.value`

`resolve_locator_params(value, params)` uses `_LOCATOR_PARAM_PATTERN = re.compile(r"\$\{([^}]+)\}")` — non-anchored, all embedded tokens. [VERIFIED: src/actions/value_resolver.py line 24]

Any `${index}` token anywhere in `locator.value` (e.g. `"amount_${index}"` or `"//input[@id='amount_${index}']"`) is matched. The replacement function looks up `params["index"]`. If `"index"` is not in `params`, it raises `ValueError` with message `"Unknown locator param '${index}'. Workflow params: [...]"`.

**Conclusion:** Phase 21 path requires NO changes. The `merged_params` dict passed to `ActionFactory` for each iteration must contain `"index"`. As long as the `_run_section` expansion loop injects `{"index": str(i)}` into the merged params, the existing `resolve_locator_params` handles it correctly.

---

## Pydantic Field/Validator Design for `index_range`

### Installed version: Pydantic v2 (2.13.4) [VERIFIED: pip show]

The project uses `from pydantic import BaseModel, Field, field_validator, model_validator` (v2 API). [VERIFIED: src/models/workflow_models.py line 5]

### Recommended field definition

```python
# On ElementDefinition:
index_range: Optional[List[int]] = None
```

This is the minimal change. `Optional[List[int]]` is backward-compatible: all existing JSON without `index_range` deserializes as `None`.

### Validator

Add a second clause to the existing `@model_validator(mode="after")` method `value_required_for_input_actions`, or add a separate `@model_validator(mode="after")` for clarity:

```python
@model_validator(mode="after")
def validate_index_range(self) -> ElementDefinition:
    if self.index_range is None:
        return self
    if len(self.index_range) != 2:
        raise ValueError(
            f"Element '{self.name}': index_range must be a 2-element list [start, end], "
            f"got {len(self.index_range)} elements."
        )
    start, end = self.index_range
    if start > end:
        raise ValueError(
            f"Element '{self.name}': index_range start ({start}) must be <= end ({end})."
        )
    return self
```

**Why `@model_validator` not `@field_validator`:** The validator needs to reference `self.name` for the error message, which a `@field_validator` for `index_range` cannot do (it only sees the field value). `@model_validator(mode="after")` has access to the full model. [VERIFIED: pydantic v2 behavior, codebase pattern in workflow_models.py lines 90-100]

### D-06 future-proofing for per-index values

The `value: Optional[Any] = None` field on `ElementDefinition` already accepts any JSON type. A future phase could allow `value: ["100", "200", "300"]` — a list — as the per-index value form. Since `value` is typed `Optional[Any]`, no schema change is needed for that future enhancement. The current implementation ignores lists in `value` and passes the list object to `ValueResolver.resolve`, which returns it unchanged (non-string passthrough). For Phase 22, this is harmless since D-05 specifies a single string value for all indices.

To make the future path explicit without breaking anything, the engine's expansion loop can document this as a commented `TODO`:
```python
# D-06: same value for all indices; a future phase may pass value[i] when value is a list
resolved_value_for_all = element.value
```

---

## `${index}` Reservation — Collision with Workflow `params`

### The collision scenario

If a workflow JSON declares `"parameters": [{"name": "index", "value": "42"}]`, `self._params` will contain `"index"`. In the expansion loop, the code merges: `merged_params = {**self._params, "index": str(i)}`. The loop-scoped value wins (it's last in the merge), silently overriding the workflow param named `"index"`. The workflow author's `params.index` is shadowed without warning.

### Recommended enforcement

Add a validation check in `WorkflowLoader.load` (or in a `@model_validator` on `WorkflowDefinition`) that rejects a parameter named `"index"`:

```python
# In WorkflowLoader.load, after building params dict:
if "index" in params:
    raise WorkflowValidationError(
        "'index' is a reserved parameter name and cannot be used as a workflow parameter name. "
        "It is used by the index_range loop expansion feature.",
        path=str_path,
    )
```

**Alternatively**, if a reserved-name check on all future reserved words is anticipated, a `frozenset` of reserved names can be maintained in `src/core/constants.py`.

**Why fail-loud at load time:** Silently shadowing at execution time would be extremely confusing to debug (wrong locators with no error). Fail-loud at load time surfaces the error immediately with a clear message. This is consistent with the project's fail-loud pattern (Phase 21 D-05, Phase 17).

**Important:** The reservation only applies when an element in the workflow uses `index_range`. A workflow that uses the name `"index"` in `parameters` but has no `index_range` elements could arguably be allowed. However, detecting this selectively at load time is complex; a simpler rule is to reserve `"index"` unconditionally at load time, since it is a short generic name that is unlikely to be intended as a workflow parameter in practice.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Non-anchored token substitution in `name` | Custom regex | `str.replace("${index}", str(i))` or reuse `_LOCATOR_PARAM_PATTERN` | Already exists; `name` only needs `${index}`, not full multi-token expansion |
| Anchored token resolution for element value | New resolver | `resolve_dynamic_value(value, params=merged_params)` — already handles `params` lookup | Phase 17 added this tier; just inject `"index"` into params |
| Embedded locator expansion | New regex | `resolve_locator_params(value, params)` via `ActionFactory._resolve_locator` | Phase 21 added this; non-anchored, already handles all embedded `${...}` |
| Continue-on-failure loop | New try/except in loop | `_run_element` already catches and returns; `_run_section` loop continues naturally | Existing contract of `_run_element` is exactly this |
| Skip-signal on missing index | New exception type | `SkipElementSignal` already raised by `ActionFactory.run` when `skip_if_not_visible` | Exact same code path, zero changes |

**Key insight:** Every behavior required by D-07/D-08/D-09 already exists in the engine. The expansion loop in `_run_section` is the only new code beyond the model field/validator. Total new lines of logic: approximately 15-20.

---

## Common Pitfalls

### Pitfall 1: Mutating `self._params` instead of creating a merged copy

**What goes wrong:** If the expansion loop does `self._params["index"] = str(i)` instead of creating `merged_params = {**self._params, "index": str(i)}`, subsequent elements in the same section (non-indexed elements after the indexed one) will incorrectly have `"index"` in their params, potentially causing `ValueError` if they have `${index}` in a locator that was not intended.
**How to avoid:** Always create a per-iteration copy: `merged_params = {**self._params, "index": str(i)}`. Never mutate `self._params`.
**Warning signs:** Tests pass in isolation but fail when a non-indexed element follows an indexed one in the same section.

### Pitfall 2: Passing the template element (with `${index}` in name) to `ctx.at_element`

**What goes wrong:** `ExecutionContext.at_element(element.name)` is called in `_run_section`. If the template element name `"amount_${index}"` is passed instead of the concrete name `"amount_0"`, the StepResult will show the template name, not the per-index name (violates D-04).
**How to avoid:** Substitute the name before calling `ctx.at_element(concrete_name)` and before passing the element copy to `_run_element`.
**Warning signs:** StepResult shows `amount_${index}` instead of `amount_0`, `amount_1`, etc.

### Pitfall 3: `model_copy(update={"name": concrete_name})` does not re-run validators

**What goes wrong:** Pydantic v2's `model_copy(update=...)` creates a shallow copy with updated fields but does NOT re-run `@model_validator`. This is actually desired behavior here — the original validation already passed, and we only want to replace `name`. However, if the validator is later changed to check `name` for `${index}` presence, it won't fire on the copy.
**How to avoid:** Document that `model_copy` is used deliberately and that validators are not re-run on copies. This is a feature, not a bug, for this use case. [VERIFIED: pydantic v2 behavior]

### Pitfall 4: `index_range` present but `${index}` absent from name/locator

**What goes wrong:** An element has `index_range: [0, 3]` but neither `name` nor `locator.value` contains `${index}`. All four iterations run with the same concrete name and locator. The engine records four identical StepResults under the same name, and the same locator is targeted four times. This may be intentional (click the same button 4 times) but is likely an authoring error.
**How to avoid:** Add a warning log (not an error) when `index_range` is present but no `${index}` token is found in `name` or `locator.value`. A strict mode could raise, but a warning is less disruptive.
**Warning signs:** Four identical rows in the test report under the same element name.

### Pitfall 5: `required=True` and `value=None` validator fires on template element before expansion

**What goes wrong:** The existing `value_required_for_input_actions` validator checks `self.action in input_actions and self.value is None and self.required`. If the author sets `required=True` and value is provided (e.g. `"100"`), validation passes. But if value is `None` and `required=True`, it raises at model construction time before the engine even sees the element — this is intentional existing behavior and is unchanged. No special handling needed for `index_range` elements here.
**How to avoid:** No action needed — the existing validator correctly fires at model construction (i.e. JSON load time), which is the right time.

### Pitfall 6: Pydantic v2 `field_validator` vs `model_validator` for `index_range`

**What goes wrong:** A `@field_validator("index_range")` cannot access `self.name` for the error message; Pydantic v2 field validators only receive the field value.
**How to avoid:** Use `@model_validator(mode="after")` — the existing pattern in `ElementDefinition`. [VERIFIED: src/models/workflow_models.py lines 90-100]

---

## Code Examples

### 1. `index_range` field + validator on `ElementDefinition`
```python
# Source: src/models/workflow_models.py — extending ElementDefinition

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class ElementDefinition(BaseModel):
    name: str
    type: ElementType
    action: ActionType
    locator: LocatorDefinition
    value: Optional[Any] = None
    required: bool = False
    wait_condition: Optional[WaitConditionDefinition] = None
    pre_wait: Optional[WaitConditionDefinition] = None
    post_wait: Optional[WaitConditionDefinition] = None
    options: Optional[Dict[str, Any]] = None
    assertions: Optional[List[AssertionDefinition]] = None
    retryable: bool = False
    retry_count: int = Field(default=0, ge=0, le=10)
    # Phase 22: optional loop range; None means single-element (no loop)
    index_range: Optional[List[int]] = None

    @model_validator(mode="after")
    def value_required_for_input_actions(self) -> ElementDefinition:
        # ... existing validator body unchanged ...

    @model_validator(mode="after")
    def validate_index_range(self) -> ElementDefinition:
        if self.index_range is None:
            return self
        if len(self.index_range) != 2:
            raise ValueError(
                f"Element '{self.name}': index_range must be a 2-element list [start, end], "
                f"got {len(self.index_range)} element(s)."
            )
        start, end = self.index_range
        if start > end:
            raise ValueError(
                f"Element '{self.name}': index_range start ({start}) must be <= end ({end})."
            )
        return self
```
[VERIFIED: codebase — pattern matches existing model_validator in workflow_models.py lines 90-100]

### 2. Expansion loop in `_run_section`
```python
# Source: src/workflow/workflow_engine.py — _run_section method

def _run_section(self, section: SectionDefinition, ctx: ExecutionContext) -> None:
    logger.info("[Section] %s", section.name)
    dyn_section = DynamicSection(self._driver, self._wm, section, self._screenshots)

    for element in section.elements:
        if element.index_range is None:
            # Existing path: single element, no expansion
            self._run_element(element, dyn_section, ctx.at_element(element.name))
        else:
            # Phase 22: loop expansion
            start, end = element.index_range
            for i in range(start, end + 1):
                # Create per-iteration merged params (never mutate self._params)
                merged_params = {**self._params, "index": str(i)}
                # Substitute ${index} in name so StepResult shows concrete name (D-04)
                concrete_name = element.name.replace("${index}", str(i))
                concrete_elem = element.model_copy(update={"name": concrete_name})
                logger.info(
                    "[Group] %s index=%d -> element '%s'",
                    element.name, i, concrete_name,
                )
                self._run_element(
                    concrete_elem,
                    dyn_section,
                    ctx.at_element(concrete_name),
                    params_override=merged_params,
                )
```

### 3. `_run_element` signature extension (backward-compatible)
```python
# Source: src/workflow/workflow_engine.py — _run_element method

def _run_element(
    self,
    element: ElementDefinition,
    section: DynamicSection,
    ctx: ExecutionContext,
    params_override: dict | None = None,   # Phase 22: per-index merged params
) -> None:
    logger.info(
        "[Element] %s | action=%s type=%s",
        element.name, element.action.value, element.type.value,
    )
    params = params_override if params_override is not None else self._params
    factory = ActionFactory(section, self._wm, params=params)
    start_ms = time.monotonic()
    # ... rest of the try/except block unchanged ...
```
[VERIFIED: codebase — ActionFactory already accepts params kwarg, workflow_engine.py line 132]

### 4. Reserved name check in `WorkflowLoader.load`
```python
# Source: src/data/json_loader.py — in WorkflowLoader.load, after building params dict

_RESERVED_PARAM_NAMES = frozenset({"index"})

# After: params[p["name"]] = resolved_value
if p["name"] in _RESERVED_PARAM_NAMES:
    raise WorkflowValidationError(
        f"Parameter name '{p['name']}' is reserved by the framework "
        f"(used for index_range loop expansion) and cannot be used as a workflow parameter.",
        path=str_path,
    )
```

### 5. JSON authoring example (from CONTEXT.md D-02/D-03)
```json
{
  "name": "amount_${index}",
  "type": "number",
  "action": "input",
  "locator": { "by": "id", "value": "amount_${index}" },
  "index_range": [0, 3],
  "value": "100"
}
```
Produces: `amount_0`, `amount_1`, `amount_2`, `amount_3` — each set to `"100"`, each its own StepResult.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-element dispatch in `_run_section` | Single-element dispatch; group elements require duplication | Before Phase 22 | Authoring burden: N similar elements must be written N times |
| `${param}` anchored-only in values | Anchored for values (Phase 17), partial/embedded for locators (Phase 21) | Phase 21 | Two coexisting modes; `${index}` fits the partial locator mode |
| No loop construct in workflow JSON | `index_range: [start, end]` inclusive | **Phase 22** | Eliminates repetition for indexed element groups |

---

## Assumptions Log

All claims in this research are verified from direct inspection of the codebase. No assumed (unverified) claims.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | None — all claims verified from source | — | — |

---

## Open Questions (RESOLVED)

All three questions were resolved during planning (Phase 22 plans 22-01 / 22-02).

1. **`${index}` absent from `name` when `index_range` is set**
   - What we know: The engine would still loop and run the same element name N times.
   - What's unclear: Should this be a warning, a hard error, or silently allowed?
   - **RESOLVED: warn, do not fail.** Plan 02 Task 3 adds a WARNING-level log from `_run_section` when `index_range` is set but `${index}` appears in neither `name` nor `locator.value` (Pitfall 4). This allows deliberate use cases like "click the same button N times" while flagging likely authoring mistakes.

2. **`index_range` with `required=True` and `value=None` (sparse index groups)**
   - What we know: The existing model validator for `value_required_for_input_actions` fires at model construction, before the engine sees the element. If `required=True` and `value=None`, it raises at load time.
   - What's unclear: Should `required` semantics be relaxed for indexed groups?
   - **RESOLVED: no change.** `required=True` + `value=None` is still an authoring error regardless of `index_range`. The existing validator constraint is unchanged; Plan 02 does not touch it.

3. **`index_range` on an element with assertions**
   - What we know: `AssertionDefinition` is a per-element list. The `model_copy` for the concrete element carries over the same assertions. If assertions reference `${index}` in their locator, the locator resolver will not expand it (assertions pass locators through a different path).
   - What's unclear: Does Phase 22 scope include assertions?
   - **RESOLVED: out of scope for Phase 22.** Assertion locators are not expanded in Phase 21 either; the plans do not touch the assertion path. If a future phase expands assertion locators, `${index}` will work automatically via the same merged-params seam.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is code-only, no new external CLI tools or services.

---

## Validation Architecture

`workflow.nyquist_validation: true` in `.planning/config.json` — section required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project-configured) |
| Config file | `pytest.ini` or `pyproject.toml` (project root) |
| Quick run command | `pytest tests/unit/test_workflow_models.py tests/unit/test_index_expansion.py -v` |
| Full suite command | `pytest tests/unit/ -v` |

### Phase Requirements → Test Map

Behaviors derived from CONTEXT.md decisions D-01..D-09:

| Req ID | Behavior | Test Type | Automated Command | File |
|--------|----------|-----------|-------------------|------|
| D-01 | `index_range` field accepted on `ElementDefinition`, `None` by default | unit | `pytest tests/unit/test_workflow_models.py::TestIndexRange::test_no_index_range_defaults_to_none -x` | Wave 0 |
| D-02a | `index_range: [0, 3]` produces indices 0, 1, 2, 3 (four calls to `_run_element`) | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_range_0_to_3_produces_four_calls -x` | Wave 0 |
| D-02b | `index_range: [start, end]` with `start > end` raises `ValidationError` at model construction | unit | `pytest tests/unit/test_workflow_models.py::TestIndexRange::test_start_greater_than_end_raises -x` | Wave 0 |
| D-02c | `index_range` with length ≠ 2 raises `ValidationError` at model construction | unit | `pytest tests/unit/test_workflow_models.py::TestIndexRange::test_length_not_2_raises -x` | Wave 0 |
| D-03 | `${index}` substituted embedded mid-string in `locator.value` (e.g. `"amount_${index}"` → `"amount_2"`) | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_embedded_index_in_locator_value -x` | Wave 0 |
| D-03b | `${index}` substituted in XPath locator (e.g. `"//input[@id='amount_${index}']"` → `"//input[@id='amount_2']"`) | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_xpath_locator_with_index -x` | Wave 0 |
| D-04 | `${index}` substituted in element `name` → StepResult shows concrete name | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_step_result_shows_concrete_name -x` | Wave 0 |
| D-05 | Same `value` applied to all iterations | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_same_value_all_indices -x` | Wave 0 |
| D-07 | N StepResults recorded for N indices | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_n_results_for_n_indices -x` | Wave 0 |
| D-08 | Failed index does not stop remaining indices in the group | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_failed_index_does_not_stop_group -x` | Wave 0 |
| D-09 | Missing index + `skip_if_not_visible=True` → SKIPPED (not FAILED) | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_missing_index_skipped_when_skip_flag -x` | Wave 0 |
| D-09b | Missing index without `skip_if_not_visible` → FAILED, group continues | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_missing_index_failed_without_skip_flag -x` | Wave 0 |
| reserved | `${index}` reserved: workflow param named `index` raises `WorkflowValidationError` at load | unit | `pytest tests/unit/test_json_loader.py::TestReservedParamName::test_index_param_raises -x` | Wave 0 |
| no-regression | Non-indexed elements in the same section still work exactly as before | unit | `pytest tests/unit/test_index_expansion.py::TestIndexExpansion::test_non_indexed_element_unchanged -x` | Wave 0 |
| no-regression | Existing `_run_element` tests still pass (backward compat of `params_override=None`) | unit | `pytest tests/unit/test_action_dispatch.py -x` | Existing |

### Test Implementation Guidance

**`tests/unit/test_index_expansion.py` (new file)**

The engine-level tests need to run `_run_section` or `_run_element` without a browser. Pattern: mock `DynamicSection` and `WaitManager`; use a real `ResultCollector`; inspect `collector.summary().steps` for names and statuses.

```python
# Pattern for D-08 test (failed index, group continues)
mock_factory_run = MagicMock(side_effect=[
    None,                          # index 0: pass
    ElementActionError("fail"),    # index 1: fail
    None,                          # index 2: pass
])
```

This requires either mocking `ActionFactory.run` or the lower-level `DynamicSection` methods. The cleanest approach: mock `ActionFactory.run` at the point where the engine creates it.

**`tests/unit/test_workflow_models.py` — add `TestIndexRange` class**

Follow the existing `TestElementDefinition` pattern (construct via `ElementDefinition(...)`, assert `ValidationError` for invalid shapes).

### Sampling Rate
- **Per task commit:** `pytest tests/unit/test_workflow_models.py tests/unit/test_index_expansion.py -x`
- **Per wave merge:** `pytest tests/unit/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_index_expansion.py` — covers D-01..D-09, reserved-name, no-regression
- [ ] `tests/unit/test_workflow_models.py::TestIndexRange` class — covers Pydantic validation of `index_range`
- [ ] `tests/unit/test_json_loader.py::TestReservedParamName` class — covers reserved `index` param enforcement

*(Existing `test_action_dispatch.py` covers skip_if_not_visible path — no Wave 0 gap there.)*

---

## Security Domain

`security_enforcement` is not set to false in config — evaluating ASVS categories.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (partial) | `index_range` validated at model construction time (Pydantic v2 validators); `${index}` reserved name check fails-loud at load time |
| V6 Cryptography | no | — |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Locator injection via `${index}` | Tampering | `index_range` is integer-only; `str(i)` produces a safe decimal string with no special characters; no SQL or XPath injection risk from integer substitution |
| Unbounded loop from large `index_range` | DoS | `end - start` is not bounded by the model; consider a maximum range constant (e.g. 1000 iterations) as a hard limit in the validator — optional but a good safety guard |

**Note on unbounded range:** An `index_range: [0, 999999]` would produce 1 million browser interactions. A practical maximum (e.g. 1000) in the validator would prevent accidental test runs from hanging indefinitely. Whether to add this limit is Claude's Discretion.

---

## Sources

### Primary (HIGH confidence — direct source inspection)
- `src/models/workflow_models.py` — `ElementDefinition` field structure, existing `@model_validator`, Pydantic v2 API usage
- `src/workflow/workflow_engine.py` — `_run_section` loop structure, `_run_element` signature and try/except block, `ActionFactory` construction with `params`
- `src/actions/value_resolver.py` — `_PLACEHOLDER_PATTERN` (anchored), `_LOCATOR_PARAM_PATTERN` (non-anchored), `resolve_dynamic_value`, `resolve_locator_params`, `ValueResolver`
- `src/actions/action_factory.py` — `_resolve_locator`, `run`, `skip_if_not_visible` probe, `SkipElementSignal`
- `src/locators/locator_resolver.py` — `LocatorResolver.resolve` (static, params-unaware — confirmed Phase 21 seam was upstream in ActionFactory)
- `src/core/exceptions.py` — `SkipElementSignal`, `ElementActionError`, `WaitTimeoutError` signatures
- `src/data/json_loader.py` — `WorkflowLoader.load` params construction, `WorkflowValidationError` usage
- `src/workflow/execution_context.py` — `ExecutionContext.at_element` shows `element_name` is the key field for result tracking
- `.planning/phases/22-support-updating-a-group-of-similar-web-elements-together-sa/22-CONTEXT.md` — all locked decisions D-01..D-09
- `.planning/phases/21-support-locator-value-from-workflow-parameters-e-g-locator-v/21-CONTEXT.md` — Phase 21 seam decision (upstream in ActionFactory, not in LocatorResolver)
- `.planning/phases/17-support-parameter-value-expansion/17-PATTERNS.md` — Phase 17 params plumbing pattern, `ValueResolver` and `resolve_dynamic_value` extension pattern
- `tests/unit/test_locator_resolver.py` — confirmed Phase 21 seam is `ActionFactory._resolve_locator` (TestLocatorResolverWithParams class)
- `pip show pydantic` — version 2.13.4 confirmed

### Secondary (MEDIUM confidence)
- None required — all critical facts verified from source.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — single internal extension, no new packages
- Architecture (seam recommendation): HIGH — derived from direct code inspection of both caller (`_run_section`) and callee (`_run_element`) interfaces, confirmed by Phase 21 seam precedent
- Pitfalls: HIGH — derived from actual code behavior (Pydantic v2 `model_copy`, `self._params` mutability, `model_validator` scope limitations)
- Validation architecture: HIGH — test behaviors map directly 1:1 to D-01..D-09 decisions

**Research date:** 2026-06-11
**Valid until:** Stable for the lifetime of the codebase (no external dependencies to go stale)
