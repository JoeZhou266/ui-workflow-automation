# Phase 21: Support Locator Value from Workflow Parameters — Research

**Researched:** 2026-06-09
**Domain:** Python / Selenium selector parameterization, regex expansion, locator resolution seam
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Locator values support **partial/embedded** expansion — every `${param}` found
  anywhere in the selector string is expanded, not just a full-value token.
  E.g. `//div[@id='${company_code}']` and `#row-${id}` both work.
- **D-02:** This requires a **non-anchored** scan/replace path for locators, distinct from
  the existing anchored `_PLACEHOLDER_PATTERN` (`^\$\{([^}]+)\}$`) used for element values.
- **D-03:** Partial/embedded expansion applies to **locators only**. Element values keep
  Phase 4's deliberate anchored full-value-only behavior unchanged — no regression risk to
  the 402 existing unit tests. The codebase will have two distinct expansion modes (anchored
  for values, partial for locators), which is accepted.
- **D-04:** Embedded locator tokens resolve **from the workflow `params` block only**.
  `${env:KEY}` and dynamic generators (`${sin_number}`, `${first_name}`, etc.) are NOT
  resolved inside locators.
- **D-05:** An embedded `${token}` that is **not** a defined workflow param causes a
  **raise / fail-loud** — the step is recorded FAILED with a clear message naming the
  missing param.

### Claude's Discretion

- Exact regex used for the non-anchored scan, the new function/method name, and whether the
  partial resolver lives in `value_resolver.py` alongside `resolve_dynamic_value` or in a
  dedicated helper.
- Where params are threaded for locator resolution. Today `LocatorResolver.resolve()` is a
  static method with no `params` access and is the single chokepoint
  (`LocatorDefinition` → `(By, value)` tuple) used by element actions, the
  `skip_if_not_visible` visibility probe, and wait/page-readiness locators. Planner decides
  whether to (a) thread `params` into `LocatorResolver`, (b) resolve `locator.value`
  upstream in `ActionFactory` before the resolver, or (c) another seam.
- Exact wording of the error and log messages.

### Deferred Ideas (OUT OF SCOPE)

- **Non-element locator expansion** (pre_wait/post_wait conditions, load_criteria,
  spinner_locator, overlay_locator): not locked. May come for free depending on seam choice.
- **`${env:KEY}` / dynamic generators inside locators**: explicitly out of scope (D-04).
</user_constraints>

---

## Summary

Phase 21 extends the existing `${param}` expansion mechanism (introduced for element values
in Phase 17) to work inside locator `value` strings, with one key difference: element values
use an **anchored** pattern (whole string must be the token), while locators need a
**non-anchored** scan/replace (the token can be embedded anywhere in a CSS or XPath string).

The codebase already has everything needed except the non-anchored function itself:
the `params` dict flows from `WorkflowEngine._params` into `ActionFactory`, the
`LocatorResolver.resolve()` static method is the single chokepoint that converts
`LocatorDefinition → (By, selector_string)`, and the error shape to mirror is
`ValueError("Unknown placeholder '${x}'. ...")` from `resolve_dynamic_value`.

The planner's central decision is **where to apply expansion**: at `LocatorResolver.resolve`
(gets all call sites including pre_wait/post_wait spinner/overlay locators for free) or
upstream in `ActionFactory.run` (narrower blast radius, but non-element locators stay raw).
Research concludes that threading `params` into `LocatorResolver.resolve` as an optional
parameter is the cleanest seam: zero change to callers that don't need params (they pass
`None` or omit the arg), and the shared chokepoint gives broad coverage without per-callsite
wiring.

**Primary recommendation:** Add `resolve_locator_params(value: str, params: dict) -> str` to
`value_resolver.py` using `re.sub(r"\$\{([^}]+)\}", repl, value)`. Add an optional
`params: dict | None = None` argument to `LocatorResolver.resolve`. All other call sites
remain untouched.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Locator param expansion (new function) | Actions layer (`src/actions/value_resolver.py`) | — | Lives beside `resolve_dynamic_value`; reuses same params dict shape |
| Locator resolution seam (wiring) | Locators layer (`src/locators/locator_resolver.py`) | — | Single chokepoint for all `LocatorDefinition → (By, value)` conversions |
| Params supply | Workflow layer (`workflow_engine.py` → `ActionFactory`) | — | `self._params` already flows here per Phase 17 |
| Test coverage | `tests/unit/test_locator_resolver.py` + `test_value_resolver.py` | — | Mirrors existing test file pairing |

---

## Standard Stack

No new external packages required. This phase adds a function and extends an existing method
signature.

### Existing Libraries in Use

| Library | Version in use | Role |
|---------|---------------|------|
| `re` (stdlib) | Python 3.14 builtin | Non-anchored regex scan/replace |
| `pydantic` | v2 (confirmed in codebase) | `LocatorDefinition` model (unchanged) |
| `selenium` | installed | `By` constants (unchanged) |

**Installation:** None required. [VERIFIED: codebase inspection]

---

## Package Legitimacy Audit

> No external packages are introduced in this phase. Section not applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
WorkflowEngine._params (dict)
        │
        ▼ passed at construction
ActionFactory(params=self._params)          [existing]
        │
        ▼ .run(element)
        ├─ skip_if_not_visible probe
        │      └─ BasePage.is_visible(element.locator)
        │              └─ LocatorResolver.resolve(locator, params=params)  [NEW param]
        │                      └─ expand_locator_params(value, params)     [NEW fn]
        │                              └─ re.sub(r"\$\{([^}]+)\}", ...)
        │
        ├─ ValueResolver.resolve(element.value)         [UNCHANGED anchored path]
        │
        ├─ WaitManager.wait_for_condition(pre_wait)
        │      └─ LocatorResolver.resolve(locator)      [params=None → no change]
        │
        ├─ ElementActions.execute(element, resolved_value)
        │      └─ BasePage.*( element.locator )
        │              └─ LocatorResolver.resolve(locator, params=params)  [NEW param]
        │
        └─ WaitManager.wait_for_condition(post_wait)
               └─ LocatorResolver.resolve(locator)      [params=None → no change]
```

**Key:** calls to `LocatorResolver.resolve` with `params=None` (or omitting `params`) expand
nothing, preserving exact existing behavior. Only paths that receive a non-None `params` dict
will attempt expansion.

### Recommended Project Structure

No new files or folders. Changes are confined to:

```
src/
├── actions/
│   └── value_resolver.py      # ADD resolve_locator_params() function
└── locators/
    └── locator_resolver.py    # ADD params kwarg to LocatorResolver.resolve()
tests/
└── unit/
    ├── test_value_resolver.py  # ADD TestLocatorParamExpansion class
    └── test_locator_resolver.py # ADD TestLocatorResolverWithParams class
```

### Pattern 1: Non-Anchored Partial Expansion Function

**What:** A standalone function in `value_resolver.py` that uses `re.sub` with a non-anchored
pattern to replace every `${param}` occurrence in an arbitrary string.

**When to use:** Called only from `LocatorResolver.resolve` when `params` is not None.

```python
# Source: [VERIFIED: codebase inspection + Python re stdlib docs] [ASSUMED: function name]
_LOCATOR_PARAM_PATTERN = re.compile(r"\$\{([^}]+)\}")

def resolve_locator_params(value: str, params: dict) -> str:
    """Replace every embedded ``${param}`` token in a locator selector string.

    Unlike :func:`resolve_dynamic_value`, this performs a non-anchored scan so
    tokens embedded inside XPath or CSS selectors are expanded in-place.

    Only ``params`` dict keys are resolved — env config and dynamic generators
    are intentionally excluded (D-04).

    Args:
        value: Raw locator value string, may contain zero or more ``${param}`` tokens.
        params: Workflow parameters dict (name → resolved string value).

    Returns:
        The selector with every ``${param}`` token substituted.

    Raises:
        ValueError: If any ``${token}`` in ``value`` is not found in ``params``.
    """
    def _replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in params:
            raise ValueError(
                f"Unknown locator param '${{key}}'. "
                f"Workflow params: {sorted(params)}"
            )
        return str(params[key])

    return _LOCATOR_PARAM_PATTERN.sub(_replace, value)
```

**Verified behavior (regression-tested locally):**

| Input | params | Output |
|-------|--------|--------|
| `//div[@id='${company_code}']` | `{'company_code': 'ACME'}` | `//div[@id='ACME']` |
| `#row-${id}` | `{'id': '42'}` | `#row-42` |
| `${company_code}` | `{'company_code': 'ACME'}` | `ACME` |
| `.class_${type}_box` | `{'type': 'admin'}` | `.class_admin_box` |
| `no_token` | `{}` | `no_token` |
| `${missing}` | `{}` | raises `ValueError` |

[VERIFIED: codebase inspection — Python `re.sub` with callable repl tested manually]

### Pattern 2: Extending LocatorResolver.resolve with Optional params

**What:** Add `params: dict | None = None` to the static method signature. When `params` is
not None and the locator value contains any `${…}` token, call `resolve_locator_params`.

**When to use:** All existing callers pass no `params` (backward compatible). Only
`ActionFactory` and callers that have params access pass a non-None dict.

```python
# Source: [VERIFIED: codebase inspection — src/locators/locator_resolver.py:27]
@staticmethod
def resolve(
    locator: LocatorDefinition,
    element_name: str = "",
    params: dict | None = None,         # NEW optional kwarg
) -> Tuple[str, str]:
    by_key = locator.by.lower().strip()
    selenium_by = _BY_MAP.get(by_key)
    if selenium_by is None:
        raise LocatorResolutionError(by=locator.by, element_name=element_name)
    value = locator.value
    if params is not None:
        from src.actions.value_resolver import resolve_locator_params
        value = resolve_locator_params(value, params)
    return selenium_by, value
```

**Blast radius:** Zero — every existing call site passes 0 or 1 positional args; the new
`params` kwarg defaults to `None` and activates no new code path.

### Pattern 3: Wiring params in ActionFactory

**What:** `ActionFactory` receives `params` at construction (existing). The `run()` method
needs to thread `params` to the locator resolution calls it owns.

**Current call sites in ActionFactory.run (line 44):**

```python
# src/actions/action_factory.py:43-44
if element.options and element.options.get("skip_if_not_visible"):
    if not self._page.is_visible(element.locator):
```

`BasePage.is_visible(locator)` calls `LocatorResolver.resolve(locator)` at line 74 of
`base_page.py`. To thread params, the planner must decide whether to:

**(a) Thread params through BasePage methods** — changes multiple method signatures in
`base_page.py` and `base_component.py`.

**(b) Resolve locator value upstream in ActionFactory** — mutate or copy the locator before
passing it to page methods. Side effect: creates a new `LocatorDefinition` with the resolved
value.

**(c) Store params on ActionFactory and pass them to LocatorResolver.resolve at call sites
that ActionFactory controls** — requires changing the `is_visible()` call and the
`execute()` dispatch.

Research recommendation: **(b) resolve upstream in ActionFactory** is the lowest blast
radius. Before calling `self._page.is_visible(element.locator)` and before calling
`self._executor.execute(element, resolved_value)`, produce a resolved locator:

```python
# In ActionFactory.run(), before skip_if_not_visible check:
resolved_locator = self._resolve_locator(element.locator)
# Then use resolved_locator everywhere element.locator is referenced in this method
```

```python
def _resolve_locator(self, locator: LocatorDefinition) -> LocatorDefinition:
    if not self._params:
        return locator
    from src.actions.value_resolver import resolve_locator_params
    resolved_value = resolve_locator_params(locator.value, self._params)
    if resolved_value == locator.value:
        return locator  # no tokens — reuse original
    return LocatorDefinition(by=locator.by, value=resolved_value)
```

This keeps all BasePage/BaseComponent signatures unchanged. The resolved
`LocatorDefinition` is passed where `element.locator` is currently passed.

**Implication for non-element locators:** With option (b), pre_wait/post_wait locators
and load_criteria locators are NOT automatically expanded (they flow through WaitManager →
LocatorResolver without params). This is acceptable per CONTEXT.md Deferred section.

### Anti-Patterns to Avoid

- **Using the anchored `_PLACEHOLDER_PATTERN` for locator expansion:** The anchored pattern
  (`^\$\{…\}$`) returns no match for embedded tokens. Do NOT reuse it. [VERIFIED: codebase]
- **Modifying `resolve_dynamic_value` to support partial expansion:** The existing function
  has deliberate anchored semantics. Changing it would break the VP-09 test
  ("partial token not expanded") and violate D-03. [VERIFIED: test_value_resolver.py:353]
- **Using `LocatorDefinition` validator during resolution:** `LocatorDefinition.by` has a
  validator that rejects unknown strategies. When creating a resolved copy, `by` is
  unchanged, so no validator issue occurs.
- **Mutating `element.locator` in-place:** `LocatorDefinition` is a Pydantic model;
  mutating fields directly is unreliable in Pydantic v2 without `model_config =
  ConfigDict(frozen=False)`. Always create a new instance.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Regex for token scan | Custom state-machine parser | `re.compile(r"\$\{([^}]+)\}")` | Handles all edge cases, well-tested |
| Partial string replacement | String split/join | `re.sub(pattern, callable, string)` | Callable repl raises `ValueError` inside sub correctly |
| LocatorDefinition copy | Dict manipulation | `LocatorDefinition(by=..., value=...)` | Pydantic model validates `by` field |

**Key insight:** Python's `re.sub` with a callable replacement function propagates exceptions
raised inside the callable — if the callable raises `ValueError` for an unknown token,
`re.sub` propagates it immediately without substituting further. This is the correct fail-loud
behavior for D-05. [VERIFIED: Python stdlib behavior]

---

## Common Pitfalls

### Pitfall 1: re.sub callable exceptions propagate correctly — but only for Python exceptions

**What goes wrong:** Developer assumes `re.sub` swallows exceptions from the repl callable.
**Why it happens:** Some regex engines silently skip failed substitutions.
**How to avoid:** Python's `re.sub` propagates any exception raised in the callable. A
`ValueError` for an unknown `${x}` token will surface immediately and bubble up through
`LocatorResolver.resolve` → `ActionFactory._resolve_locator` → `ActionFactory.run` → the
`except Exception` catch in `WorkflowEngine._run_element`, which records the step as FAILED.
**Warning signs:** If tests show a partial substitution occurred (some tokens expanded, later
one silently skipped), the repl function is not raising as expected.
[VERIFIED: Python re docs + manual test in this session]

### Pitfall 2: Anchored pattern returns None for embedded tokens

**What goes wrong:** Developer passes an embedded selector like `//div[@id='${x}']` to
`resolve_dynamic_value`. The anchored `_PLACEHOLDER_PATTERN` does not match, the function
returns the string unchanged, and the locator hits the browser as a literal `${x}` selector.
**Why it happens:** The distinction between the two patterns is subtle.
**How to avoid:** Never call `resolve_dynamic_value` for locator expansion. The new
`resolve_locator_params` function with the non-anchored pattern is the only correct path.
**Warning signs:** Browser error "unable to locate element" with `${` visible in the selector
in the error message or screenshot.
[VERIFIED: codebase — _PLACEHOLDER_PATTERN at value_resolver.py:15]

### Pitfall 3: LocatorDefinition validator rejects the resolved copy

**What goes wrong:** Creating `LocatorDefinition(by=locator.by, value=resolved_value)` fails
if `locator.by` was already validated to a known strategy but the copy triggers validation
again.
**Why it happens:** Pydantic v2 runs validators on `__init__`. The `by_must_be_known`
validator allows all 8 strategies (`id`, `name`, etc.) — these are the same values already
stored in `locator.by`, so re-validation always succeeds.
**How to avoid:** No action needed — the validated `by` value is always one of the 8 allowed
strategies, so the copy constructor succeeds.
[VERIFIED: workflow_models.py:16-24]

### Pitfall 4: params=None vs params={} distinction

**What goes wrong:** Treating `params=None` as "no params" and `params={}` as "has params but
empty" inconsistently. If a locator contains `${x}` and `params={}`, the function must still
raise `ValueError` (D-05) — not silently skip expansion.
**Why it happens:** `if params is not None` vs `if params` differ when params is `{}`.
**How to avoid:** In `LocatorResolver.resolve`, gate on `params is not None` (not `if
params`). In `_resolve_locator` in ActionFactory, gate on `if not self._params` (which
treats `{}` as "no expansion needed" — this is safe because an empty params dict with a
`${x}` locator will still call `resolve_locator_params`, which will raise `ValueError`).
Actually: use `if params is not None` consistently at the resolver level so the error fires.
[VERIFIED: value_resolver.py:201 — `if params is not None and key in params` pattern]

### Pitfall 5: The skip_if_not_visible probe uses element.locator before value resolution

**What goes wrong:** ActionFactory.run() checks skip_if_not_visible at line 43 using
`element.locator` before any resolution. If the locator contains `${x}`, `is_visible` fails
with an unrecognized selector in the browser (or a `ValueError` from the new code if
threaded). The element is incorrectly treated as not-visible and skipped.
**Why it happens:** The skip check happens before the existing `resolved_value` computation
at line 50.
**How to avoid:** Compute `resolved_locator = self._resolve_locator(element.locator)` at the
TOP of `ActionFactory.run()`, before the skip_if_not_visible check. Use `resolved_locator`
for the `is_visible` call and for all subsequent `element.locator` references.
[VERIFIED: action_factory.py:43-50]

---

## Research Question Answers

### Q1: Non-anchored regex for embedded expansion

**Answer:** `re.compile(r"\$\{([^}]+)\}")` — verified to work correctly for all selector
syntax patterns. [VERIFIED: manual test in this session]

- Matches every `${param}` anywhere in the string
- Handles multiple tokens in one string (e.g. `//div[@id='${a}']/span[@class='${b}']`)
- Handles adjacent text before and after the token
- Handles XPath string quotes inside attribute predicates
- Handles CSS `#`/`.` prefixes
- Handles no-token strings (zero substitutions, returns original)

Using `re.sub(pattern, callable_repl, value)` where the callable raises `ValueError` on
unknown token correctly surfaces the error immediately.

### Q2: Resolver seam — recommended option

**Recommendation: Option (b) — resolve `locator.value` upstream in `ActionFactory`.**

Rationale:

| Option | Call Sites Changed | Non-element locators auto-expand | Complexity |
|--------|--------------------|----------------------------------|-----------|
| (a) Thread params into LocatorResolver | 1 static method signature + all callers with params | Yes (all) | Medium — must thread params through BasePage, WaitManager, PageReadiness |
| (b) Resolve upstream in ActionFactory | ActionFactory only | No (pre_wait/post_wait, load_criteria stay raw) | Low — 1 private method on ActionFactory |
| (c) Another seam (e.g. at element model level) | WorkflowEngine | Depends | Would require changing how element.locator is accessed everywhere |

Option (b) wins on blast radius: only `ActionFactory` changes. The deferred non-element
coverage is acceptable per CONTEXT.md. If coverage is later needed, adding `params` to
`LocatorResolver.resolve` is still possible as a follow-up (the optional kwarg approach
in Pattern 2 above).

**Alternative note:** Option (a) — threading params directly into `LocatorResolver.resolve`
as an optional kwarg — is also clean and would give free coverage for non-element locators.
The planner may choose (a) if broad coverage is valued. The signature change is backward
compatible (`params=None` default). The complication is that WaitManager.wait_for_condition
and PageReadinessChecker call `LocatorResolver.resolve` and would need to receive `params`
too — they don't currently have access to `params`, so this requires threaded params through
WaitManager or a context object.

### Q3: Params plumbing path (verified from source)

```
json_loader.py:119-131  WorkflowLoader.load()
    ├─ params[p["name"]] = resolve_dynamic_value(p["value"])  # env expansion at load time
    └─ (params dict returned from WorkflowLoader, not directly exposed)

workflow_engine.py:61-64  WorkflowEngine.__init__()
    self._params: dict = {
        p.name: resolve_dynamic_value(p.value)
        for p in (self._definition.parameters or [])
    }
    # NOTE: params are built again here — json_loader also builds them for $ref condition eval

workflow_engine.py:132  WorkflowEngine._run_element()
    factory = ActionFactory(section, self._wm, params=self._params)

action_factory.py:22-26  ActionFactory.__init__()
    self._resolver = ValueResolver(params=params)
    # params stored on self._params? No — only on ValueResolver.
    # The params dict passed in is NOT stored as self._params on ActionFactory.
```

**Critical discovery:** `ActionFactory` does NOT store `params` as `self._params`. It passes
`params` only to `ValueResolver`. The planner must add `self._params = params or {}` to
`ActionFactory.__init__` to enable locator expansion.

[VERIFIED: action_factory.py:22-26 — only `self._resolver = ValueResolver(params=params)`]

### Q4: Non-element locator coverage through LocatorResolver

Call sites of `LocatorResolver.resolve` in the codebase (verified by grep):

| File | Line | Context | Has params access? |
|------|------|---------|-------------------|
| `base_page.py` | 59,64,74,96,102,108,126,139,150,161,176 | All BasePage interaction methods | No (no params on BasePage) |
| `base_component.py` | 41,53,61 | Component scoped find methods | No |
| `wait_manager.py` | 128 | `wait_for_condition` main locator | No |
| `wait_manager.py` | 191 | `_wait_gone` (spinner/overlay) | No |
| `page_readiness.py` | 68,76 | spinner_locator, overlay_locator | No |

**Conclusion:** No existing `LocatorResolver.resolve` call site has access to `params` except
through ActionFactory. If option (b) is chosen, the resolved locator is passed to BasePage
methods which call `LocatorResolver.resolve` again on the already-resolved value — which is
fine because the resolved value has no `${…}` tokens left.

With option (b), non-element locators (pre_wait/post_wait `locator`, `spinner_locator`,
`overlay_locator`, `load_criteria.locator`) are NOT expanded. These are all deferred per
CONTEXT.md.

### Q5: Unknown-token behavior from Phase 17 (D-05)

In `resolve_dynamic_value` (value_resolver.py:203-207):

```python
raise ValueError(
    f"Unknown placeholder '${{{key}}}'. "
    f"Registered keys: {sorted(PLACEHOLDER_REGISTRY)}"
    + (f". Workflow params: {sorted(params)}" if params is not None else "")
)
```

Test confirming this shape (test_value_resolver.py:127-128):
```python
def test_unknown_placeholder_raises(self):
    with pytest.raises(ValueError, match="Unknown placeholder"):
        resolve_dynamic_value("${nonexistent_key}")
```

The locator path should raise `ValueError` with a parallel shape:
```
"Unknown locator param '${key}'. Workflow params: ['param1', 'param2']"
```

This `ValueError` propagates through `ActionFactory._resolve_locator` →
`ActionFactory.run()` → caught by `except Exception as exc:` in `workflow_engine.py:166`
→ recorded as FAILED with message `"Unexpected: Unknown locator param '${x}'..."`.

[VERIFIED: workflow_engine.py:166-174, exceptions.py]

### Q6: Regression safety — what must NOT change

The 402 unit tests (confirmed by `pytest --collect-only`) cover:

- `tests/unit/test_value_resolver.py` — 40+ tests including `VP-09: test_partial_token_not_expanded`
  which asserts that `"prefix_${name}"` is returned unchanged by `resolve_dynamic_value`.
  This test MUST continue to pass.
- `tests/unit/test_locator_resolver.py` — 8 tests asserting current static behavior.
  All must pass. The new tests are additions, not modifications.

**The anchored `_PLACEHOLDER_PATTERN` and `resolve_dynamic_value` must not be touched.**
[VERIFIED: test_value_resolver.py:353, value_resolver.py:15]

### Q7: Test patterns to mirror

`test_locator_resolver.py` pattern:
- Class `TestLocatorResolver` with `@pytest.mark.parametrize` for strategy matrix
- Constructs `LocatorDefinition(by=..., value=...)` directly
- Calls `LocatorResolver.resolve(locator)` or `LocatorResolver.resolve(locator, element_name="x")`
- No fixtures, no browser

`test_value_resolver.py` pattern:
- Multiple `class TestXxx` groupings (one per feature area)
- Test method IDs in docstrings (e.g. `# VP-01`)
- Uses `pytest.raises(ValueError, match="...")` for error assertions
- No fixtures needed for pure functions

**New test class should be:** `class TestLocatorParamExpansion` in
`tests/unit/test_locator_resolver.py` plus a matching `class TestResolveLocatorParams` in
`tests/unit/test_value_resolver.py` for the standalone function.

---

## Code Examples

### Verified: Anchored pattern (unchanged — element values)

```python
# Source: src/actions/value_resolver.py:15
_PLACEHOLDER_PATTERN = re.compile(r"^\$\{([^}]+)\}$")
# Returns None for "//div[@id='${x}']" — this is intentional for element values
```

### Verified: Non-anchored pattern (new — locator values)

```python
# Source: [VERIFIED: manual test in this session]
_LOCATOR_PARAM_PATTERN = re.compile(r"\$\{([^}]+)\}")
# Matches every ${token} anywhere in the string
```

### Verified: ActionFactory construction receives params

```python
# Source: src/workflow/workflow_engine.py:132
factory = ActionFactory(section, self._wm, params=self._params)

# Source: src/actions/action_factory.py:22
def __init__(self, page: BasePage, wait_manager: WaitManager, params: dict | None = None) -> None:
    self._executor = ElementActions(page, wait_manager)
    self._wm = wait_manager
    self._page = page
    self._resolver = ValueResolver(params=params)
    # NOTE: params is NOT stored as self._params here — must add this line
```

### Verified: WorkflowEngine builds params dict

```python
# Source: src/workflow/workflow_engine.py:61-64
self._params: dict = {
    p.name: resolve_dynamic_value(p.value)
    for p in (self._definition.parameters or [])
}
```

### Verified: LocatorDefinition model (unchanged)

```python
# Source: src/models/workflow_models.py:10-25
class LocatorDefinition(BaseModel):
    by: str = Field(...)
    value: str = Field(...)

    @field_validator("by")
    @classmethod
    def by_must_be_known(cls, v: str) -> str:
        allowed = {"id", "name", "class_name", "css_selector",
                   "xpath", "link_text", "partial_link_text", "tag_name"}
        if v not in allowed:
            raise ValueError(...)
        return v
```

### Verified: LocatorResolver.resolve current signature (to extend)

```python
# Source: src/locators/locator_resolver.py:27-44
@staticmethod
def resolve(locator: LocatorDefinition, element_name: str = "") -> Tuple[str, str]:
    by_key = locator.by.lower().strip()
    selenium_by = _BY_MAP.get(by_key)
    if selenium_by is None:
        raise LocatorResolutionError(by=locator.by, element_name=element_name)
    return selenium_by, locator.value   # <-- returns raw value today
```

---

## Runtime State Inventory

> Omitted — this is a greenfield feature addition, not a rename/refactor/migration phase.

---

## Environment Availability

> Step 2.6: SKIPPED — phase adds Python code only; no external tools, services, or CLIs
> beyond Python 3.14.5 and the already-installed packages (all confirmed present).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (confirmed from pytest cache files) |
| Config file | `pytest.ini` or `conftest.py` in project root |
| Quick run command | `pytest tests/unit/test_locator_resolver.py tests/unit/test_value_resolver.py -v` |
| Full suite command | `pytest tests/unit/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LP-01 | `resolve_locator_params("//div[@id='${x}']", {"x": "ACME"})` returns `//div[@id='ACME']` | unit | `pytest tests/unit/test_value_resolver.py::TestResolveLocatorParams -x` | Wave 0 |
| LP-02 | `resolve_locator_params("#row-${id}", {"id": "42"})` returns `#row-42` | unit | `pytest tests/unit/test_value_resolver.py::TestResolveLocatorParams -x` | Wave 0 |
| LP-03 | Multiple tokens in one string all expanded | unit | `pytest tests/unit/test_value_resolver.py::TestResolveLocatorParams -x` | Wave 0 |
| LP-04 | No token in string — returned unchanged | unit | `pytest tests/unit/test_value_resolver.py::TestResolveLocatorParams -x` | Wave 0 |
| LP-05 | Unknown `${x}` raises `ValueError` naming the param | unit | `pytest tests/unit/test_value_resolver.py::TestResolveLocatorParams::test_unknown_token_raises -x` | Wave 0 |
| LP-06 | `LocatorResolver.resolve(locator, params={"x":"v"})` expands token | unit | `pytest tests/unit/test_locator_resolver.py::TestLocatorResolverWithParams -x` | Wave 0 |
| LP-07 | `LocatorResolver.resolve(locator)` with no params — unchanged (regression) | unit | `pytest tests/unit/test_locator_resolver.py -x` | Exists |
| LP-08 | `ActionFactory.run` with parameterized locator resolves before probe | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_action_factory_integration -x` | Exists (extend) |
| LP-09 | Element value anchored behavior still intact (`prefix_${name}` unchanged) | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_partial_token_not_expanded -x` | Exists |
| LP-10 | WorkflowEngine passes params to ActionFactory (existing chain verified) | unit | `pytest tests/unit/test_workflow_params.py -x` | Exists |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/test_locator_resolver.py tests/unit/test_value_resolver.py -x`
- **Per wave merge:** `pytest tests/unit/ -v`
- **Phase gate:** Full suite 402 + new tests green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_value_resolver.py` — ADD `class TestResolveLocatorParams` with LP-01..LP-05
- [ ] `tests/unit/test_locator_resolver.py` — ADD `class TestLocatorResolverWithParams` with LP-06..LP-07

*(Existing test infrastructure fully covers the runner; only new test classes needed)*

---

## Security Domain

> `security_enforcement` not explicitly set to false in config.json — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes — locator values from params could inject selector syntax | No external input; params come from workflow JSON, not end-user input. No sanitization needed beyond fail-loud on unknown tokens. |
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V6 Cryptography | No | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Selector injection via param values | Tampering | Params originate from workflow JSON (operator-controlled, not end-user). CSS/XPath injection is an operator risk, not a framework responsibility. Framework expands verbatim. |
| `${env:KEY}` bypass attempt in locator | Elevation of Privilege | D-04 explicitly excludes env resolution from locator path. The new function checks `params` dict only, never `_ENV_CONFIG`. |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The recommended function name `resolve_locator_params` | Patterns | Name only — planner may choose any name; no behavior impact |
| A2 | The recommended helper `ActionFactory._resolve_locator` | Patterns | Planner may choose a different wiring strategy (option a or c); seam analysis still valid |
| A3 | New `TestResolveLocatorParams` test class name | Validation Architecture | Name only |

**All behavioral claims are [VERIFIED: codebase inspection] unless tagged [ASSUMED].**

---

## Open Questions

1. **Non-element locator expansion (deferred):**
   - What we know: pre_wait/post_wait conditions, load_criteria, spinner_locator, and
     overlay_locator all go through `LocatorResolver.resolve` in WaitManager and
     PageReadinessChecker, neither of which has params access.
   - What's unclear: Whether a future phase should thread params through WaitManager or use a
     different approach.
   - Recommendation: Document as deferred. If option (a) is chosen for this phase (params
     kwarg on LocatorResolver.resolve), then WaitManager would need a matching change to pass
     params — defer that to a separate phase.

2. **ActionFactory self._params storage:**
   - What we know: `ActionFactory.__init__` passes `params` only to `ValueResolver`, does not
     store it as `self._params`. This must change.
   - What's unclear: Whether storing `params or {}` is preferable to `params` (keeping None
     distinct from empty dict).
   - Recommendation: Store `self._params: dict = params or {}` for consistency with
     `ValueResolver.__init__` (line 228 of value_resolver.py: `self._params: dict = params or {}`).

---

## Sources

### Primary (HIGH confidence)

- `src/actions/value_resolver.py` — anchored pattern, `resolve_dynamic_value`, `ValueResolver` class; all claims verified by direct file read
- `src/locators/locator_resolver.py` — `LocatorResolver.resolve` static method signature and return; verified
- `src/actions/action_factory.py` — params plumbing, `self._resolver = ValueResolver(params=params)`, no `self._params` storage; verified
- `src/workflow/workflow_engine.py:61-64,132` — `self._params` construction and ActionFactory construction; verified
- `src/models/workflow_models.py` — `LocatorDefinition` model, `LocatorDefinition.by_must_be_known` validator; verified
- `src/ui/base_page.py` — all 11 `LocatorResolver.resolve` call sites; verified
- `src/waits/wait_manager.py` — 2 `LocatorResolver.resolve` call sites including `_wait_gone`; verified
- `src/waits/page_readiness.py` — 2 `LocatorResolver.resolve` call sites for spinner/overlay; verified
- `src/ui/base_component.py` — 3 `LocatorResolver.resolve` call sites; verified
- `tests/unit/test_value_resolver.py` — existing test patterns, VP-09 test, error message shape; verified
- `tests/unit/test_locator_resolver.py` — existing test patterns; verified
- Python `re.sub` with callable repl — exception propagation behavior verified by manual test in this session

### Secondary (MEDIUM confidence)

- 402 test count confirmed by `pytest tests/unit/ --collect-only -q`
- `gsd-sdk query init.phase-op "21"` — phase directory and config confirmed

---

## Metadata

**Confidence breakdown:**
- New function (`resolve_locator_params`): HIGH — direct code and regex verification
- Seam analysis: HIGH — all call sites traced from source
- Params plumbing: HIGH — traced from WorkflowEngine through ActionFactory line by line
- Pitfall list: HIGH — each pitfall references specific verified line numbers
- Test patterns: HIGH — existing test files read and compared

**Research date:** 2026-06-09
**Valid until:** 2026-07-09 (stable codebase — no external dependencies)
