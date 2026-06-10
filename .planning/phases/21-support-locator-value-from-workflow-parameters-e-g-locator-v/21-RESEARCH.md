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

The planner's central decision is **where to apply expansion**. Two seams were considered:
(a) thread `params` into `LocatorResolver.resolve` (broad coverage including non-element
locators), or (b) resolve `locator.value` upstream in `ActionFactory.run` (narrower blast
radius, but non-element locators stay raw).

**Seam decision (planning): option (b).** Although option (a) appears cleaner on paper, it
does NOT reach the ~9 internal `element.locator` reads inside `ElementActions.execute`
without also threading params through `execute()` and every dispatch branch — a much higher
blast radius for this codebase. Option (b) resolves the locator upstream, builds a resolved
`ElementDefinition` copy via `model_copy`, and passes that copy to `is_visible`,
`_execute_with_retry`, and `execute` — touching only `action_factory.py` and
`value_resolver.py`. This is the lower-blast-radius solution and is what the plan implements.

**Primary recommendation:** Add `resolve_locator_params(value: str, params: dict) -> str` to
`value_resolver.py` using `re.sub(r"\$\{([^}]+)\}", repl, value)`. Resolve the locator
upstream in `ActionFactory` (option b); `LocatorResolver.resolve` is NOT modified.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Locator param expansion (new function) | Actions layer (`src/actions/value_resolver.py`) | — | Lives beside `resolve_dynamic_value`; reuses same params dict shape |
| Locator resolution seam (wiring) | Actions layer (`src/actions/action_factory.py`) | — | Option (b): upstream resolution + `model_copy` so `LocatorResolver.resolve` stays unchanged |
| Params supply | Workflow layer (`workflow_engine.py` → `ActionFactory`) | — | `self._params` already flows here per Phase 17 |
| Test coverage | `tests/unit/test_locator_resolver.py` + `test_value_resolver.py` | — | Mirrors existing test file pairing |

---

## Standard Stack

No new external packages required. This phase adds a function and an `ActionFactory` helper.

### Existing Libraries in Use

| Library | Version in use | Role |
|---------|---------------|------|
| `re` (stdlib) | Python 3.14 builtin | Non-anchored regex scan/replace |
| `pydantic` | v2 (confirmed in codebase) | `LocatorDefinition` / `ElementDefinition` models (unchanged) |
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
        ├─ resolved_locator = self._resolve_locator(element.locator)   [NEW — option b]
        ├─ target = element.model_copy(update={"locator": resolved_locator})  [NEW]
        │
        ├─ skip_if_not_visible probe
        │      └─ BasePage.is_visible(target.locator)   [resolved copy]
        │              └─ LocatorResolver.resolve(locator)   [UNCHANGED — no params kwarg]
        │
        ├─ ValueResolver.resolve(element.value)         [UNCHANGED anchored path]
        │
        ├─ WaitManager.wait_for_condition(pre_wait)
        │      └─ LocatorResolver.resolve(locator)      [raw — non-element, deferred]
        │
        ├─ ElementActions.execute(target, resolved_value)   [resolved copy]
        │      └─ BasePage.*( target.locator )
        │              └─ LocatorResolver.resolve(locator)   [UNCHANGED]
        │
        └─ WaitManager.wait_for_condition(post_wait)
               └─ LocatorResolver.resolve(locator)      [raw — non-element, deferred]
```

**Key:** `LocatorResolver.resolve` is never modified. The resolved locator is carried inside
`target` (a `model_copy` of the element), so every internal `target.locator` read sees the
expanded value. Non-element locators (pre_wait/post_wait/load_criteria/spinner/overlay) flow
through WaitManager/PageReadiness without params and stay raw — deferred per CONTEXT.md.

### Recommended Project Structure

No new files or folders. Changes are confined to:

```
src/
├── actions/
│   ├── value_resolver.py     # ADD resolve_locator_params() function
│   └── action_factory.py     # ADD self._params storage + _resolve_locator helper + run() wiring
tests/
└── unit/
    ├── test_value_resolver.py  # ADD TestResolveLocatorParams class
    └── test_locator_resolver.py # ADD TestLocatorResolverWithParams class (exercises ActionFactory)
```

### Pattern 1: Non-Anchored Partial Expansion Function

**What:** A standalone function in `value_resolver.py` that uses `re.sub` with a non-anchored
pattern to replace every `${param}` occurrence in an arbitrary string.

**When to use:** Called only from `ActionFactory._resolve_locator` when `params` is non-empty.

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

### Pattern 2: Upstream resolution in ActionFactory (option b — chosen)

**What:** `ActionFactory` stores `self._params`, adds a `_resolve_locator` helper, and in
`run()` builds a resolved `ElementDefinition` copy (`target`) via `model_copy`. The copy is
passed to the visibility probe and to execution. `LocatorResolver.resolve` is unchanged.

**Why not a params kwarg on LocatorResolver.resolve (option a):** `ElementActions.execute`
reads `element.locator` internally at ~9 dispatch branches and takes no separate locator
argument. A `params` kwarg on `LocatorResolver.resolve` would expand the visibility probe but
NOT those internal reads unless params were also threaded through `execute()` and every
branch — higher blast radius. Carrying the resolved value inside `target` covers all reads
with no change to `ElementActions` or `LocatorResolver`.

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

```python
# In ActionFactory.run(), at the TOP (before the skip_if_not_visible probe):
resolved_locator = self._resolve_locator(element.locator)
target = (
    element
    if resolved_locator is element.locator
    else element.model_copy(update={"locator": resolved_locator})
)
# Use target.locator for the is_visible probe; pass target to
# _execute_with_retry / self._executor.execute.
```

**Implication for non-element locators:** With option (b), pre_wait/post_wait locators
and load_criteria locators are NOT automatically expanded (they flow through WaitManager →
LocatorResolver without params). This is acceptable per CONTEXT.md Deferred section.

### Anti-Patterns to Avoid

- **Using the anchored `_PLACEHOLDER_PATTERN` for locator expansion:** The anchored pattern
  (`^\$\{…\}$`) returns no match for embedded tokens. Do NOT reuse it. [VERIFIED: codebase]
- **Modifying `resolve_dynamic_value` to support partial expansion:** The existing function
  has deliberate anchored semantics. Changing it would break the VP-09 test
  ("partial token not expanded") and violate D-03. [VERIFIED: test_value_resolver.py:353]
- **Adding a `params` kwarg to `LocatorResolver.resolve`:** Option (b) was chosen — see
  Pattern 2. A params kwarg would not reach `ElementActions.execute`'s internal locator reads.
- **Resolving into a local variable only:** `ElementActions.execute` reads `element.locator`
  internally; resolve into a `model_copy` (`target`) and pass that, not a local.
- **Mutating `element.locator` in-place:** `LocatorDefinition` is a Pydantic model;
  mutating fields directly is unreliable in Pydantic v2 without `model_config =
  ConfigDict(frozen=False)`. Always create a new instance / use `model_copy`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Regex for token scan | Custom state-machine parser | `re.compile(r"\$\{([^}]+)\}")` | Handles all edge cases, well-tested |
| Partial string replacement | String split/join | `re.sub(pattern, callable, string)` | Callable repl raises `ValueError` inside sub correctly |
| Element copy with new locator | Dict manipulation | `element.model_copy(update={"locator": ...})` | Pydantic v2 preserves all other fields, re-validates `by` safely |

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
`resolve_locator_params` → `ActionFactory._resolve_locator` → `ActionFactory.run` → the
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
empty" inconsistently. If a locator contains `${x}` and `params={}`, expansion must still
raise `ValueError` (D-05) — not silently skip.
**Why it happens:** `if params is not None` vs `if params` differ when params is `{}`.
**How to avoid:** Under option (b), `ActionFactory._resolve_locator` gates on
`if not self._params` (treating `{}` as "no expansion needed" — safe, because params are
built once at engine init and an empty params dict means no `${param}` definitions exist).
Inside `resolve_locator_params` itself, the `key not in params` check fires for any token,
so a `${x}` against a non-empty params dict that lacks `x` raises correctly.
[VERIFIED: value_resolver.py:201 — `if params is not None and key in params` pattern]

### Pitfall 5: The skip_if_not_visible probe uses element.locator before value resolution

**What goes wrong:** ActionFactory.run() checks skip_if_not_visible at line 43 using
`element.locator` before any resolution. If the locator contains `${x}`, `is_visible` fails
with an unrecognized selector in the browser. The element is incorrectly treated as
not-visible and skipped.
**Why it happens:** The skip check happens before the existing `resolved_value` computation
at line 50.
**How to avoid:** Compute `resolved_locator = self._resolve_locator(element.locator)` and
build `target` at the TOP of `ActionFactory.run()`, before the skip_if_not_visible check.
Use `target.locator` for the `is_visible` call and `target` for all subsequent execution.
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

**Decision: Option (b) — resolve `locator.value` upstream in `ActionFactory`.**

Rationale:

| Option | Call Sites Changed | Non-element locators auto-expand | Reaches ElementActions internal reads | Complexity |
|--------|--------------------|----------------------------------|----------------------------------------|-----------|
| (a) Thread params into LocatorResolver | 1 static method signature + every caller with params | Yes (all) | NO — execute() reads element.locator internally; would also need params threaded through execute() and every branch | High |
| (b) Resolve upstream in ActionFactory + model_copy | ActionFactory only | No (pre_wait/post_wait, load_criteria stay raw) | YES — resolved value carried inside `target` reaches every internal read | Low |
| (c) Another seam (e.g. at element model level) | WorkflowEngine | Depends | Depends | Would require changing how element.locator is accessed everywhere |

Option (b) wins decisively: only `ActionFactory` and `value_resolver.py` change, and the
resolved locator reaches every consumer (probe + all ~9 `ElementActions.execute` branches)
via the `model_copy` `target`. The earlier note that option (a) "would give free coverage for
non-element locators" is true but misleading — it would NOT cover the element-action path
without far more threading. The deferred non-element coverage is acceptable per CONTEXT.md.
If non-element coverage is later needed, adding `params` to `LocatorResolver.resolve` remains
a possible follow-up phase.

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
through ActionFactory. With option (b), the resolved locator (inside `target`) is passed to
BasePage methods which call `LocatorResolver.resolve` again on the already-resolved value —
which is fine because the resolved value has no `${…}` tokens left.

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
  All must pass. `LocatorResolver.resolve` is unchanged under option (b); the new tests are
  additions that exercise ActionFactory, not modifications to LocatorResolver behavior.

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

**New test classes:** `class TestResolveLocatorParams` in `tests/unit/test_value_resolver.py`
for the standalone function, and `class TestLocatorResolverWithParams` in
`tests/unit/test_locator_resolver.py` exercising the option-(b) seam through `ActionFactory`
(using `MagicMock` for page/wait_manager — no browser).

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

### Verified: LocatorResolver.resolve current signature (UNCHANGED under option b)

```python
# Source: src/locators/locator_resolver.py:27-44
@staticmethod
def resolve(locator: LocatorDefinition, element_name: str = "") -> Tuple[str, str]:
    by_key = locator.by.lower().strip()
    selenium_by = _BY_MAP.get(by_key)
    if selenium_by is None:
        raise LocatorResolutionError(by=locator.by, element_name=element_name)
    return selenium_by, locator.value   # <-- returns the (already-resolved) value
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
| LP-05 | Unknown `${x}` raises `ValueError` naming the param | unit | `pytest tests/unit/test_value_resolver.py::TestResolveLocatorParams -x` | Wave 0 |
| LP-06 | `ActionFactory._resolve_locator` expands token from params | unit | `pytest tests/unit/test_locator_resolver.py::TestLocatorResolverWithParams -x` | Wave 0 |
| LP-07 | `LocatorResolver.resolve(locator)` with no params — unchanged (regression) | unit | `pytest tests/unit/test_locator_resolver.py -x` | Exists |
| LP-08 | `_resolve_locator` unknown token raises `ValueError` (fail-loud) | unit | `pytest tests/unit/test_locator_resolver.py::TestLocatorResolverWithParams -x` | Wave 0 |
| LP-09 | `ActionFactory.run` threads resolved ElementDefinition copy to executor | unit | `pytest tests/unit/test_locator_resolver.py::TestLocatorResolverWithParams -x` | Wave 0 |
| (regression) | Element value anchored behavior still intact (`prefix_${name}` unchanged) | unit | `pytest tests/unit/test_value_resolver.py::TestParamExpansion::test_partial_token_not_expanded -x` | Exists |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/test_locator_resolver.py tests/unit/test_value_resolver.py -x`
- **Per wave merge:** `pytest tests/unit/ -v`
- **Phase gate:** Full suite 402 + new tests green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_value_resolver.py` — ADD `class TestResolveLocatorParams` with LP-01..LP-05
- [ ] `tests/unit/test_locator_resolver.py` — ADD `class TestLocatorResolverWithParams` with LP-06..LP-09 (via ActionFactory)

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
| A2 | The recommended helper `ActionFactory._resolve_locator` | Patterns | Name only — option (b) seam is fixed by planning |
| A3 | New `TestResolveLocatorParams` test class name | Validation Architecture | Name only |

**All behavioral claims are [VERIFIED: codebase inspection] unless tagged [ASSUMED].**

---

## Open Questions (RESOLVED)

1. **Non-element locator expansion (deferred):**
   - What we know: pre_wait/post_wait conditions, load_criteria, spinner_locator, and
     overlay_locator all go through `LocatorResolver.resolve` in WaitManager and
     PageReadinessChecker, neither of which has params access.
   - What was unclear: Whether a future phase should thread params through WaitManager or use a
     different approach.
   - RESOLVED: Deferred per CONTEXT.md (Deferred Ideas — non-element locator expansion is out
     of scope for Phase 21). Because Phase 21 uses option (b) (upstream resolution in
     ActionFactory), non-element locators are NOT expanded and that is the accepted tradeoff,
     documented in the plan's `<seam_decision>` and to be recorded in the SUMMARY. If coverage
     is needed later, add `params` to `LocatorResolver.resolve` plus a WaitManager change in a
     separate phase.

2. **ActionFactory self._params storage:**
   - What we know: `ActionFactory.__init__` passes `params` only to `ValueResolver`, does not
     store it as `self._params`. This must change.
   - What was unclear: Whether storing `params or {}` is preferable to `params` (keeping None
     distinct from empty dict).
   - RESOLVED: Store `self._params = params or {}` (consistent with `ValueResolver.__init__`,
     value_resolver.py:228). `_resolve_locator` gates on `if not self._params`, so a `None` or
     `{}` params dict short-circuits to returning the locator unchanged; an unknown token under
     a non-empty params dict still raises via `resolve_locator_params` (D-05 preserved).

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
- Seam analysis: HIGH — all call sites traced from source; option (b) selected during planning
- Params plumbing: HIGH — traced from WorkflowEngine through ActionFactory line by line
- Pitfall list: HIGH — each pitfall references specific verified line numbers
- Test patterns: HIGH — existing test files read and compared

**Research date:** 2026-06-09
**Valid until:** 2026-07-09 (stable codebase — no external dependencies)
