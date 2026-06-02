# Phase 17: Support Using Parameters in Element Values as Placeholders — Research

**Researched:** 2026-06-02
**Domain:** Python value resolution — parameter injection into `ValueResolver` / `ActionFactory`
**Confidence:** HIGH

---

## Summary

Phase 17 closes the loop between workflow `parameters` (introduced in Phase 11 and already parsed at load time) and element `value` fields (already passing through `ValueResolver` at runtime via `ActionFactory`). Today, these two subsystems do not communicate: workflow parameters are used exclusively for conditional `$ref` evaluation at load time, and `ValueResolver` knows only about the static `PLACEHOLDER_REGISTRY` and `${env:KEY}` placeholders. A `${account_type}` token in an element `value` field currently raises `ValueError: Unknown placeholder`.

The fix is surgical: the `ValueResolver` class needs to know the current workflow's parameters at the point when it resolves element values. The `ActionFactory` is where `ValueResolver.resolve()` is called (line 51 of `action_factory.py`), and `WorkflowEngine._run_element()` is where `ActionFactory` is instantiated (line 127 of `workflow_engine.py`). The parameters are on `WorkflowDefinition.parameters`, which `WorkflowEngine` already holds at `self._definition`.

**Critical constraint confirmed by codebase inspection:** `_PLACEHOLDER_PATTERN` uses a full-value-only match (`^` + `$` anchors via `re.compile(r"^\$\{([^}]+)\}$")`). This means `${param_name}` only resolves when the entire `value` string is the token. A value like `"Hello ${account_type}"` is returned unchanged. Phase 17 should preserve this full-value-only semantics for parameter expansion — no substring substitution. [VERIFIED: src/actions/value_resolver.py line 15]

**Resolution order:** When a key matches, the lookup order must be: (1) `${env:KEY}` namespace (already handled by key prefix check), (2) `PLACEHOLDER_REGISTRY` (dynamic generators), (3) workflow parameters (static resolved strings). This order ensures existing placeholders are not shadowed by parameter names accidentally matching a registry entry. However, a simpler and equally valid approach is: (1) `${env:KEY}`, (2) check `PLACEHOLDER_REGISTRY`, (3) if not found there, check parameters dict, (4) if not found anywhere, raise `ValueError`. The planner should choose one.

**Primary recommendation:** Add a `params: dict` argument to `ValueResolver` (or its `resolve` method) and check it in `_resolve_string` after the registry lookup fails. Wire the workflow parameters dict from `WorkflowDefinition.parameters` through `WorkflowEngine` → `ActionFactory` → `ValueResolver`. All changes are confined to `value_resolver.py`, `action_factory.py`, and `workflow_engine.py`. No model changes, no load-time changes, no new files required.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Parameter value expansion in elements | Action layer (`src/actions/`) | — | `ValueResolver` is already the sole value-processing extension point, called by `ActionFactory` for every element before dispatch |
| Workflow parameters dict propagation | Workflow layer (`src/workflow/`) | Action layer | `WorkflowEngine` owns `WorkflowDefinition` and must thread `params` dict into `ActionFactory` |
| Error on undefined parameter token | Action layer (`src/actions/`) | — | `ValueError` raised by `resolve_dynamic_value`; error message must name the unresolvable key and list available sources |
| No load-time changes | Data layer — unchanged | — | Parameters are already resolved at load time; Phase 17 is runtime-only |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `re` (stdlib) | Python 3.9+ built-in | Already the placeholder detection regex | No new dep; existing `_PLACEHOLDER_PATTERN` continues unchanged |
| `pytest` | 8.4.2 [VERIFIED: .venv/bin/pytest] | Unit tests | Already the project test runner |
| `pydantic` | 2.x [VERIFIED: .venv] | `WorkflowDefinition.parameters` already parsed as `List[ParameterDefinition]` | Existing model unchanged |

### Supporting
None — this phase uses only project internals already in place. No new dependencies.

**Installation:** No `pip install` required.

---

## Architecture Patterns

### System Architecture Diagram

```
Workflow JSON loaded → WorkflowDefinition.parameters = [ParameterDefinition(name, value)]
                                |
                                v
                    WorkflowEngine.__init__(definition)
                    self._definition.parameters → build params_dict: {name: value}
                                |
                                v
                    WorkflowEngine._run_element(element, ...)
                    factory = ActionFactory(section, self._wm, params=params_dict)  ← CHANGE
                                |
                                v
                    ActionFactory.run(element)
                    resolved_value = _resolver.resolve(element.value)
                    where _resolver = ValueResolver(params=params_dict)             ← CHANGE
                                |
                    element.value = "${account_type}"
                                |
                    ValueResolver._resolve_string("${account_type}")
                                |
                    _PLACEHOLDER_PATTERN matches → key = "account_type"
                                |
                    key.startswith("env:")? → NO
                    key in PLACEHOLDER_REGISTRY? → NO
                    key in self._params? → YES → return self._params["account_type"]
                                |
                    key in PLACEHOLDER_REGISTRY? → NO
                    key in self._params? → NO
                        → raise ValueError("Unknown placeholder '${account_type}'. ...")
```

### Recommended Project Structure

No new files. All changes are in-place modifications:

```
src/
└── actions/
    ├── value_resolver.py     # EXTEND: ValueResolver.__init__(params={}); check params in _resolve_string
    └── action_factory.py     # EXTEND: accept params kwarg; pass to ValueResolver constructor
src/
└── workflow/
    └── workflow_engine.py    # EXTEND: build params_dict from definition.parameters; pass to ActionFactory

tests/
└── unit/
    └── test_value_resolver.py  # EXTEND: add TestParamExpansion class (VP-01..VP-08)
```

### Pattern 1: Thread `params` dict through constructor chain

**What:** `WorkflowEngine` extracts `{p.name: p.value for p in definition.parameters or []}` once and passes it to every `ActionFactory` constructor. `ActionFactory` stores it and injects it into `ValueResolver`.

**When to use:** This is the standard approach for context propagation in this codebase (see how `base_url`, `default_wait_timeout`, and `screenshots_dir` are threaded from `WorkflowEngine.__init__` to subordinate objects).

**Example:**
```python
# src/workflow/workflow_engine.py — build params dict once in __init__ or run()
# [VERIFIED: WorkflowDefinition.parameters is Optional[List[ParameterDefinition]]]
self._params: dict = {
    p.name: p.value for p in (self._definition.parameters or [])
}

# src/workflow/workflow_engine.py — _run_element, pass params to ActionFactory
factory = ActionFactory(section, self._wm, params=self._params)

# src/actions/action_factory.py — accept and store params, create ValueResolver with params
_resolver = ValueResolver(params=params)

# src/actions/value_resolver.py — ValueResolver stores params, checks in _resolve_string
class ValueResolver:
    def __init__(self, params: dict | None = None) -> None:
        self._params: dict = params or {}

    def _resolve_string(self, value: str) -> str:
        return resolve_dynamic_value(value, params=self._params)
```

**Note on `_resolver` module-level singleton:** Currently `action_factory.py` defines `_resolver = ValueResolver()` at module level (line 15). This must change to a per-instance `ValueResolver` created in `ActionFactory.__init__`, since each factory call may carry different params. [VERIFIED: src/actions/action_factory.py line 15]

### Pattern 2: Extend `resolve_dynamic_value` to accept optional params

**What:** Add `params: dict | None = None` to `resolve_dynamic_value` signature. After checking `PLACEHOLDER_REGISTRY`, check `params` before raising.

**Example:**
```python
# src/actions/value_resolver.py
def resolve_dynamic_value(value: str, params: dict | None = None) -> str:
    """..."""
    if not isinstance(value, str):
        raise TypeError(...)
    match = _PLACEHOLDER_PATTERN.match(value)
    if not match:
        return value
    key = match.group(1)
    if key.startswith("env:"):
        # existing env: handling unchanged
        ...
    if key in PLACEHOLDER_REGISTRY:
        return PLACEHOLDER_REGISTRY[key]()
    if params and key in params:
        return str(params[key])  # str() handles int/bool parameter values
    raise ValueError(
        f"Unknown placeholder '${{{key}}}'. "
        f"Registered keys: {sorted(PLACEHOLDER_REGISTRY)}"
        + (f". Workflow params: {sorted(params)}" if params else "")
    )
```

### Anti-Patterns to Avoid

- **Module-level `_resolver` singleton in `action_factory.py`:** The current `_resolver = ValueResolver()` at module scope (line 15) works only because `ValueResolver` is stateless today. Once `ValueResolver` holds a `params` dict, this must become a per-`ActionFactory`-instance resolver to avoid cross-workflow parameter contamination in tests. Do not keep the module-level singleton.
- **Modifying `WorkflowLoader` or load-time code:** Parameters are already fully resolved at load time in `json_loader.py`. Phase 17 is a runtime concern only. No changes to `json_loader.py`, `condition_evaluator.py`, or `WorkflowDefinition` model.
- **Substring/template-string substitution:** The existing `_PLACEHOLDER_PATTERN` uses full-value-only anchors. Do not introduce `re.sub` or `str.replace` for parameter expansion. A value like `"Hello ${name}"` must continue to be returned unchanged.
- **`eval()` or `ast.literal_eval()`:** Not needed. Parameter values are already resolved strings from the `params` dict.
- **Mutating `PLACEHOLDER_REGISTRY` with parameter names:** Parameters must NOT be injected into the global registry. The registry is for generated dynamic values (SIN, name, date); parameters are static string values from the workflow JSON.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parameter lookup | Custom dict class / deep copy logic | Plain `dict` passed by reference | Params dict is already a `{str: str}` from `WorkflowLoader` — no custom structure needed |
| Token detection | New regex | Existing `_PLACEHOLDER_PATTERN` unchanged | The same `^\$\{([^}]+)\}$` regex already captures parameter names correctly |
| Thread safety | Locks / thread-local storage | Constructor-injected dict | WorkflowEngine is single-threaded per CLAUDE.md architecture; no concurrency concern |

---

## Current Placeholder Resolution Flow (VERIFIED)

This is the critical baseline. Phase 17 extends step 5.

1. **Load time** (`WorkflowLoader.load()`): Parameters are extracted from raw JSON, `${env:KEY}` tokens in parameter values are resolved via `resolve_dynamic_value()`, and the resolved `params: dict` is built. Parameters are used only for `$ref` condition evaluation (Phase 11/16). The resolved params dict is NOT stored on `WorkflowDefinition` — it is a local in `WorkflowLoader.load()`. [VERIFIED: json_loader.py lines 119–137]

2. **Runtime** (`WorkflowEngine.run()`): `WorkflowDefinition.parameters` is `Optional[List[ParameterDefinition]]` — it holds the original (pre-resolved) parameter objects with their raw `value` strings. At runtime, if a parameter's value was `"${env:ACCT_TYPE}"`, `definition.parameters[0].value` still holds the original string, NOT the resolved value. [VERIFIED: workflow_models.py lines 139–148, json_loader.py]

   **CRITICAL IMPLICATION:** When `WorkflowEngine` builds `params_dict` for Phase 17, it must re-resolve `${env:KEY}` tokens in parameter values (call `resolve_dynamic_value(p.value)` for each parameter), exactly as `WorkflowLoader.load()` does. Otherwise parameters set via `${env:KEY}` will inject the literal string `"${env:KEY}"` instead of the resolved env value.

3. **Element dispatch** (`ActionFactory.run()`): `_resolver.resolve(element.value)` is called at line 51. `ValueResolver.resolve()` calls `_resolve_string()` for string values, which calls `resolve_dynamic_value()`. This is where parameter expansion must be injected. [VERIFIED: action_factory.py line 51]

4. **Current behavior for `${param_name}`**: `resolve_dynamic_value("${account_type}")` → key `"account_type"` is not `env:`-prefixed, not in `PLACEHOLDER_REGISTRY` → raises `ValueError: Unknown placeholder '${account_type}'`. [VERIFIED: value_resolver.py lines 178–195]

---

## Edge Cases

### 1. Parameters with `${env:KEY}` values (CRITICAL — see above)
`WorkflowDefinition.parameters[i].value` stores the ORIGINAL string from JSON, not the load-time-resolved value. If the parameter was declared as `{"name": "account_type", "value": "${env:ACCT_TYPE}"}`, `definition.parameters[0].value == "${env:ACCT_TYPE}"`. The `WorkflowEngine` must call `resolve_dynamic_value(p.value)` for each parameter when building the runtime `params_dict`, not just use `p.value` directly. [VERIFIED: json_loader.py lines 119–137 vs. workflow_models.py lines 139–148]

### 2. Non-string parameter values (int, bool)
`ParameterDefinition.value` is typed as `str` in the Pydantic model [VERIFIED: workflow_models.py line 147]. This means all parameter values are strings at model validation time. No int/bool coercion is needed. However, the implementation should call `str(params[key])` defensively in case a dict is constructed outside the model.

### 3. Parameter name conflicts with PLACEHOLDER_REGISTRY keys
If a workflow declares `{"name": "sin_number", "value": "123-456-789"}`, should the parameter shadow the registry generator? **Recommendation:** Registry takes priority over parameters (PLACEHOLDER_REGISTRY checked first), so the author must avoid naming parameters after registry keys. This is consistent with the existing `env:` prefix approach which namespaces env keys to avoid conflicts. Alternatively, parameters could take priority — this is a design decision for the planner to lock. Either is implementable; document the chosen precedence clearly.

### 4. Undefined parameter token in element value
If `element.value = "${undefined_param}"` and the key is not in PLACEHOLDER_REGISTRY or params dict, the existing `ValueError` is raised. This should include both the registered keys AND the available parameter names in the error message to help authors debug.

### 5. `element.value = None`
`ValueResolver.resolve(None)` returns `None` unchanged [VERIFIED: value_resolver.py line 219]. No change needed.

### 6. `element.value` is non-string (int, bool, list)
`ValueResolver.resolve(42)` returns `42` unchanged (non-string passthrough) [VERIFIED: value_resolver.py lines 218–223]. No change needed.

### 7. Workflow has no parameters
`WorkflowDefinition.parameters` is `None` when not declared [VERIFIED: workflow_models.py line 158]. `params_dict` must default to `{}`. `ValueResolver` initialized with empty dict behaves exactly as today — no regression.

### 8. Nested `${...}` in parameter values (e.g. a parameter whose value is another `${param_name}`)
`ParameterDefinition.value` is a plain string already resolved at load time (by `resolve_dynamic_value`). At load time, `resolve_dynamic_value("${account_type}")` where `"account_type"` is not in PLACEHOLDER_REGISTRY and not in env would raise. So nested parameter references cannot exist at load time — they would fail on load. Phase 17 does not introduce recursive expansion. [ASSUMED — this deduction follows from the load-time validation behavior]

---

## Integration Points

### Where Parameters Are Currently Stored (Runtime)

`WorkflowEngine` holds `self._definition: WorkflowDefinition`. `WorkflowDefinition.parameters` is `Optional[List[ParameterDefinition]]` where each `ParameterDefinition` has `.name: str` and `.value: str`. [VERIFIED: workflow_models.py lines 139–158, workflow_engine.py lines 45–59]

### Where Value Resolution Happens

`ActionFactory.run(element)` at line 51: `resolved_value = _resolver.resolve(element.value)` where `_resolver = ValueResolver()` is a module-level singleton. This is the integration point. [VERIFIED: action_factory.py lines 15, 51]

### What Must Change

| File | Change | Lines Affected |
|------|--------|----------------|
| `src/actions/value_resolver.py` | `ValueResolver.__init__` accepts `params: dict`; `_resolve_string` passes params to `resolve_dynamic_value`; `resolve_dynamic_value` accepts `params` kwarg and checks it | ~lines 203–226 |
| `src/actions/action_factory.py` | Remove module-level `_resolver` singleton; `ActionFactory.__init__` accepts `params: dict`; creates `ValueResolver(params=params)` per instance | ~lines 15, 24–26 |
| `src/workflow/workflow_engine.py` | Build `params_dict` from `self._definition.parameters` (with `resolve_dynamic_value` for each value); pass to `ActionFactory` constructor in `_run_element` | ~lines 59, 127 |

### What Must NOT Change

- `WorkflowLoader.load()` — no changes
- `condition_evaluator.py` — no changes
- `WorkflowDefinition` / `ParameterDefinition` models — no changes
- `json_loader.py` — no changes
- Existing `resolve_dynamic_value` behavior for all currently registered placeholders — full backwards compatibility required

---

## Common Pitfalls

### Pitfall 1: Using `p.value` Directly Without Re-resolving `${env:KEY}`

**What goes wrong:** `WorkflowEngine` builds `params_dict = {p.name: p.value for p in definition.parameters}` and uses the raw string `"${env:ACCT_TYPE}"` as the parameter value at runtime instead of the resolved env value.

**Why it happens:** `WorkflowDefinition.parameters` stores original JSON strings, not load-time-resolved values. The load-time resolution is done locally in `WorkflowLoader.load()` and not persisted back to the model.

**How to avoid:** Mirror `WorkflowLoader.load()` lines 130–131: call `resolve_dynamic_value(p.value)` for each parameter when building `params_dict` in `WorkflowEngine`.

**Warning signs:** Test with `${env:KEY}` in parameter value — element receives literal string `"${env:ACCT_TYPE}"` instead of actual env value.

### Pitfall 2: Keeping the Module-Level `_resolver` Singleton

**What goes wrong:** `_resolver = ValueResolver()` at module level in `action_factory.py` means all `ActionFactory` instances share a single resolver. Once `ValueResolver` holds `_params`, the first workflow's params leak into all subsequent workflows in the same process.

**Why it happens:** The singleton was safe when `ValueResolver` was stateless. It is no longer safe once state is added.

**How to avoid:** Move resolver construction to `ActionFactory.__init__`: `self._resolver = ValueResolver(params=params)`.

**Warning signs:** Test running multiple workflows in sequence — second workflow sees first workflow's parameters.

### Pitfall 3: Incorrect Lookup Order (Registry vs. Parameters)

**What goes wrong:** Parameter named `"first_name"` or `"random_number"` shadows the PLACEHOLDER_REGISTRY generator, causing a static string to be used where a generated value was intended.

**Why it happens:** Parameters dict is checked before the registry.

**How to avoid:** Check `PLACEHOLDER_REGISTRY` first. Document that parameter names must not collide with registry keys in the workflow JSON authoring guide (or error message).

**Warning signs:** `${first_name}` returns `"Alice"` (static) instead of a random name when a parameter named `first_name` is declared.

### Pitfall 4: Error Message Does Not Help Debug

**What goes wrong:** `ValueError: Unknown placeholder '${account_type}'. Registered keys: [...]` does not list workflow parameters, so authors cannot tell whether the issue is a typo in the element value or a missing parameter declaration.

**Why it happens:** Existing error message was written before parameters existed.

**How to avoid:** Update the error message to include both registered keys and available parameter names.

---

## Code Examples

### Updated `resolve_dynamic_value` signature
```python
# Source: src/actions/value_resolver.py — extend existing function
# [VERIFIED: current signature and behavior]
def resolve_dynamic_value(value: str, params: dict | None = None) -> str:
    """Resolve a ``${placeholder}`` token to a generated or parameter value.

    Resolution order:
    1. ``${env:KEY}`` — env config lookup (existing)
    2. ``PLACEHOLDER_REGISTRY`` — dynamic generator (existing)
    3. ``params`` dict — workflow parameter values (Phase 17)

    Args:
        value: The raw string from an ElementDefinition.
        params: Optional dict of workflow parameter name → resolved string value.
    """
    if not isinstance(value, str):
        raise TypeError(
            f"resolve_dynamic_value expects a str, got {type(value).__name__!r}"
        )
    match = _PLACEHOLDER_PATTERN.match(value)
    if not match:
        return value
    key = match.group(1)
    if key.startswith("env:"):
        env_key = key[len("env:"):]
        if env_key not in _ENV_CONFIG:
            raise ValueError(
                f"Unknown env config key {env_key!r}. "
                f"Available keys: {sorted(_ENV_CONFIG)}"
            )
        return str(_ENV_CONFIG[env_key])
    if key in PLACEHOLDER_REGISTRY:
        return PLACEHOLDER_REGISTRY[key]()
    if params and key in params:
        return str(params[key])
    raise ValueError(
        f"Unknown placeholder '${{{key}}}'. "
        f"Registered keys: {sorted(PLACEHOLDER_REGISTRY)}"
        + (f". Workflow params: {sorted(params)}" if params else "")
    )
```

### Updated `ValueResolver` class
```python
# Source: src/actions/value_resolver.py — extend existing class
# [VERIFIED: current class at lines 203–226]
class ValueResolver:
    def __init__(self, params: dict | None = None) -> None:
        self._params: dict = params or {}

    def resolve(self, value: Optional[Any]) -> Optional[Any]:
        if value is None:
            return None
        if isinstance(value, str):
            return self._resolve_string(value)
        return value

    def _resolve_string(self, value: str) -> str:
        return resolve_dynamic_value(value, params=self._params)
```

### Updated `ActionFactory.__init__`
```python
# Source: src/actions/action_factory.py — replace module-level _resolver
# [VERIFIED: current structure at lines 15, 24–26]
class ActionFactory:
    def __init__(self, page: BasePage, wait_manager: WaitManager, params: dict | None = None) -> None:
        self._executor = ElementActions(page, wait_manager)
        self._wm = wait_manager
        self._page = page
        self._resolver = ValueResolver(params=params)
```

### Updated `WorkflowEngine._run_element` (call site)
```python
# Source: src/workflow/workflow_engine.py — pass params to ActionFactory
# [VERIFIED: current call at line 127]
factory = ActionFactory(section, self._wm, params=self._params)
```

### `WorkflowEngine` params dict construction
```python
# Source: src/workflow/workflow_engine.py — build once, mirror json_loader.py lines 130–131
# [VERIFIED: WorkflowDefinition.parameters type at workflow_models.py line 158]
# Must use resolve_dynamic_value to handle ${env:KEY} in parameter values
from src.actions.value_resolver import resolve_dynamic_value

self._params: dict = {
    p.name: resolve_dynamic_value(p.value)
    for p in (self._definition.parameters or [])
}
```

---

## Test IDs — New Naming Convention

The project uses phase-specific prefixes for test IDs:
- `SC-` = Phase 4 placeholder / value resolver tests (test_value_resolver.py)
- `OP-` = Phase 16 logical operator tests (test_workflow_params.py)

Phase 17 introduces **`VP-`** (Value-Parameters) as the new prefix. Tests live in a new class `TestParamExpansion` in `tests/unit/test_value_resolver.py` (preferred, since this extends `ValueResolver` behavior) or a new `TestParamValueExpansion` class in `test_workflow_params.py`. Given the change is to `value_resolver.py`, `test_value_resolver.py` is the natural home.

| ID | Behavior | Test Type |
|----|----------|-----------|
| VP-01 | `resolve_dynamic_value("${account_type}", params={"account_type": "OPEN"})` returns `"OPEN"` | unit |
| VP-02 | `resolve_dynamic_value("${account_type}", params={})` raises `ValueError` listing available params | unit |
| VP-03 | `resolve_dynamic_value("${sin_number}", params={"sin_number": "fixed"})` returns registry generator result (not the param), confirming registry priority | unit |
| VP-04 | `resolve_dynamic_value("${param_name}", params=None)` raises `ValueError` (no params, unknown key) | unit |
| VP-05 | `ValueResolver(params={"acct": "123"}).resolve("${acct}")` returns `"123"` | unit |
| VP-06 | `ValueResolver(params={}).resolve("${unknown_key}")` raises `ValueError` | unit |
| VP-07 | `ValueResolver(params={"x": "val"}).resolve(42)` returns `42` unchanged (non-string passthrough) | unit |
| VP-08 | `ValueResolver(params={"x": "val"}).resolve(None)` returns `None` | unit |
| VP-09 | `ValueResolver(params={"name": "Alice"}).resolve("prefix_${name}")` returns `"prefix_${name}"` unchanged (full-value-only semantics preserved) | unit |
| VP-10 | `ActionFactory` initialized with `params={"acct": "OPEN"}` — `run(element)` where `element.value = "${acct}"` calls `_resolver.resolve("${acct}")` → `"OPEN"` (integration via mock) | unit |

---

## State of the Art

| Old Behavior | New Behavior | When Changed | Impact |
|-------------|--------------|--------------|--------|
| `${param_name}` in element value raises `ValueError` | `${param_name}` resolves to parameter's string value | Phase 17 | Workflow authors can reuse parameters declared at workflow root in element value fields |
| `ValueResolver` is stateless, singleton at module level | `ValueResolver` holds `_params` dict; instantiated per `ActionFactory` | Phase 17 | Enables per-workflow parameter context; no cross-contamination between workflows |
| `resolve_dynamic_value(value: str) -> str` | `resolve_dynamic_value(value: str, params: dict | None = None) -> str` | Phase 17 | Backwards compatible — existing call sites (json_loader.py line 131) pass no `params` → defaults to `None` → behavior unchanged |

**Deprecated/outdated:**
- Module-level `_resolver = ValueResolver()` singleton in `action_factory.py` — replaced by per-instance resolver in `ActionFactory.__init__`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `PLACEHOLDER_REGISTRY` should take priority over workflow parameters when the same key appears in both | Edge Cases #3 | Low — design choice; planner should lock this decision. If params take priority, the implementation is equally simple (check params first). |
| A2 | Phase 17 preserves full-value-only token semantics (no substring substitution for parameters) | Architecture Patterns | Low — consistent with all prior phases and the existing regex design; changing to substring substitution would be a major architectural shift |
| A3 | `WorkflowDefinition.parameters[i].value` stores the original JSON string, NOT the resolved value | Current Placeholder Resolution Flow | CRITICAL — verified by code inspection; if wrong, the re-resolution step in WorkflowEngine would double-resolve and potentially error |

---

## Open Questions

1. **Parameter vs. registry lookup priority**
   - What we know: If a parameter is named `"sin_number"`, should it shadow the SIN generator or vice versa?
   - What's unclear: The spec does not address this conflict.
   - Recommendation: Registry first, then params. Document as a constraint in workflow JSON authoring.

2. **Error behavior: raise or return unchanged for unknown `${param_name}` tokens?**
   - What we know: Current behavior for unknown placeholders is `ValueError` (fail fast). Phase 11's condition evaluator also fails fast on undefined param names.
   - What's unclear: Should an element value with `${undefined}` silently pass through, or raise? Raising is consistent with the existing design.
   - Recommendation: Raise `ValueError`. Consistent with existing behavior. Planner should lock this.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — all code is pure Python stdlib; no tools, services, or CLIs required for this phase).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (in .venv/bin/pytest) |
| Config file | `pytest.ini` (rootdir) |
| Quick run command | `pytest tests/unit/test_value_resolver.py -v` |
| Full suite command | `pytest tests/unit/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VP-01 | `resolve_dynamic_value` returns param value when key matches | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_param_resolved_by_name -x` | Wave 0 |
| VP-02 | `resolve_dynamic_value` raises ValueError when param key not found | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_unknown_param_raises -x` | Wave 0 |
| VP-03 | Registry takes priority over params for same key | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_registry_priority_over_params -x` | Wave 0 |
| VP-04 | `resolve_dynamic_value` with no params behaves as today (backwards compat) | unit | `pytest tests/unit/test_value_resolver.py -x` (existing tests green) | ✅ existing |
| VP-05 | `ValueResolver(params={...}).resolve("${key}")` returns param value | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_value_resolver_with_params -x` | Wave 0 |
| VP-06 | `ValueResolver(params={}).resolve("${unknown}")` raises ValueError | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_value_resolver_unknown_raises -x` | Wave 0 |
| VP-07 | Non-string element value passes through unchanged | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_non_string_passthrough -x` | Wave 0 |
| VP-08 | `None` element value passes through unchanged | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_none_passthrough -x` | Wave 0 |
| VP-09 | Full-value-only: `"prefix_${name}"` is NOT expanded | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_partial_token_not_expanded -x` | Wave 0 |
| VP-10 | `ActionFactory` integration: element with `${param}` value resolves via injected params | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_action_factory_integration -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/test_value_resolver.py -v`
- **Per wave merge:** `pytest tests/unit/ -v` (all 372+ tests must remain green)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `TestParamExpansion` class in `tests/unit/test_value_resolver.py` — 10 new methods (VP-01..10). File already exists; add class only.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 17 |
|-----------|-------------------|
| Python 3.14.5; `from __future__ import annotations` retained | Use `from __future__ import annotations` in all modified files (already present); no 3.10+ syntax restrictions apply with 3.14 but keep the import for consistency |
| No `time.sleep()` | Not applicable |
| Pydantic v2 installed | `model_validate` pattern; `ParameterDefinition.value: str` — no model changes needed |
| Implicit wait stays 0; never cache `WebElement` | Not applicable |
| Never hardcode credentials | Not applicable — parameters are workflow-level, not credential storage |
| `pytest` for tests, unit tests in `tests/unit/` with no browser fixtures | Tests go in `tests/unit/test_value_resolver.py`; no `driver` fixture |

---

## Security Domain

This phase adds parameter value injection into element `value` fields. The only injection surface is the workflow JSON file itself — which is a trusted, developer-authored artifact, not user input. No ASVS V5 (input validation) concern applies because:
1. Parameters come from the workflow JSON, not from the browser or an API
2. Values are used as Selenium input strings, not in SQL queries or shell commands
3. The `_PLACEHOLDER_PATTERN` (full-value-only match) limits expansion to the entire `value` field — no template injection via partial strings

No ASVS categories apply to this phase.

---

## Sources

### Primary (HIGH confidence)
- `[VERIFIED: src/actions/value_resolver.py]` — full file read; current `ValueResolver`, `resolve_dynamic_value`, `_PLACEHOLDER_PATTERN`, `PLACEHOLDER_REGISTRY`, `_ENV_CONFIG` confirmed
- `[VERIFIED: src/actions/action_factory.py]` — module-level `_resolver = ValueResolver()` singleton at line 15; `_resolver.resolve(element.value)` at line 51
- `[VERIFIED: src/workflow/workflow_engine.py]` — `self._definition` at line 51; `ActionFactory(section, self._wm)` at line 127
- `[VERIFIED: src/models/workflow_models.py]` — `WorkflowDefinition.parameters: Optional[List[ParameterDefinition]]` line 158; `ParameterDefinition.value: str` line 147
- `[VERIFIED: src/data/json_loader.py]` — `resolve_dynamic_value(p["value"])` at lines 130–131; confirms params are re-resolved at load time, not stored on model
- `[VERIFIED: tests/unit/test_value_resolver.py]` — 44 existing tests; all passing; test class structure and naming conventions confirmed
- `[VERIFIED: tests/unit/test_workflow_params.py]` — 23 existing tests; OP-01..10 confirmed; naming pattern confirmed

### Secondary (MEDIUM confidence)
- `[CITED: .planning/phases/04-support-dynamic-placeholder-expansion/04-RESEARCH.md]` — Phase 4 research; architecture patterns for registry approach
- `[CITED: .planning/phases/11-support-workflow-parameters-conditional-ref/11-CONTEXT.md]` — Phase 11 decisions; D-06 (string-only params), D-07 (`${env:KEY}` resolved at load time)

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — codebase verified; no external packages
- Architecture: HIGH — all integration points confirmed by direct code inspection
- Pitfalls: HIGH — all identified by tracing actual code paths; edge cases verified against model types

**Research date:** 2026-06-02
**Valid until:** 2026-07-15 (stable stdlib + internal codebase; no external API changes possible)
