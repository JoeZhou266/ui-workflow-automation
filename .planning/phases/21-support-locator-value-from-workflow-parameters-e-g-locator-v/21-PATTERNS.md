# Phase 21: Support Locator Value from Workflow Parameters - Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 4 (2 modified, 2 test additions)
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/actions/value_resolver.py` | utility | transform | self (existing file gets new function) | exact — add `resolve_locator_params` beside `resolve_dynamic_value` |
| `src/actions/action_factory.py` | service | request-response | self (existing file gets `self._params` storage + `_resolve_locator` helper) | exact — follows the `ValueResolver(params=params)` plumbing already present |
| `tests/unit/test_value_resolver.py` | test | transform | self (existing file gets new `TestResolveLocatorParams` class) | exact — mirrors `TestParamExpansion` class structure |
| `tests/unit/test_locator_resolver.py` | test | transform | self (existing file gets new `TestLocatorResolverWithParams` class) | exact — mirrors `TestLocatorResolver` class structure |

---

## Pattern Assignments

### `src/actions/value_resolver.py` (utility, transform)

**Analog:** `src/actions/value_resolver.py` — the new function lives beside `resolve_dynamic_value` in the same file.

**Imports pattern** (lines 1-8) — unchanged, already present:
```python
from __future__ import annotations

import calendar
import random
import re
import secrets
from datetime import date, datetime
from typing import Any, Callable, Dict, Optional
```

**Existing anchored pattern constant** (line 15) — must NOT be changed (D-03):
```python
_PLACEHOLDER_PATTERN = re.compile(r"^\$\{([^}]+)\}$")
```

**New non-anchored constant to ADD** (insert immediately after line 15):
```python
# Non-anchored pattern for locator expansion (Phase 21).
# Unlike _PLACEHOLDER_PATTERN this matches every ${token} embedded anywhere
# in an XPath or CSS selector string.
_LOCATOR_PARAM_PATTERN = re.compile(r"\$\{([^}]+)\}")
```

**New function to ADD** (insert after `resolve_dynamic_value`, before `ValueResolver` class — circa line 209):
```python
def resolve_locator_params(value: str, params: dict) -> str:
    """Replace every embedded ``${param}`` token in a locator selector string.

    Unlike :func:`resolve_dynamic_value`, this performs a non-anchored scan so
    tokens embedded inside XPath or CSS selectors are expanded in-place.

    Only ``params`` dict keys are resolved — env config and dynamic generators
    are intentionally excluded (D-04).

    Args:
        value: Raw locator value string, may contain zero or more ``${param}`` tokens.
        params: Workflow parameters dict (name -> resolved string value).

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

**Error shape to mirror** — from `resolve_dynamic_value` lines 203-207:
```python
raise ValueError(
    f"Unknown placeholder '${{{key}}}'. "
    f"Registered keys: {sorted(PLACEHOLDER_REGISTRY)}"
    + (f". Workflow params: {sorted(params)}" if params is not None else "")
)
```
The new error mirrors this shape but is locator-specific:
`f"Unknown locator param '${{{key}}}'. Workflow params: {sorted(params)}"`

**Regression guard — VP-09 test must stay green** (test_value_resolver.py line 353):
```python
def test_partial_token_not_expanded(self):
    r = ValueResolver(params={"name": "Alice"})
    assert r.resolve("prefix_${name}") == "prefix_${name}"
```
The anchored `_PLACEHOLDER_PATTERN` on line 15 must not be touched.

---

### `src/actions/action_factory.py` (service, request-response)

**Analog:** `src/actions/action_factory.py` — the existing file already receives `params` in `__init__`; this change stores it and adds a private resolver helper.

**Current `__init__` pattern** (lines 22-26) — note that `params` is NOT stored as `self._params` today:
```python
def __init__(self, page: BasePage, wait_manager: WaitManager, params: dict | None = None) -> None:
    self._executor = ElementActions(page, wait_manager)
    self._wm = wait_manager
    self._page = page
    self._resolver = ValueResolver(params=params)
```

**Modified `__init__` — ADD `self._params` storage** (mirrors `ValueResolver.__init__` line 228: `self._params: dict = params or {}`):
```python
def __init__(self, page: BasePage, wait_manager: WaitManager, params: dict | None = None) -> None:
    self._executor = ElementActions(page, wait_manager)
    self._wm = wait_manager
    self._page = page
    self._resolver = ValueResolver(params=params)
    self._params: dict = params or {}   # ADD: needed for locator expansion (Phase 21)
```

**New private helper to ADD** (new method on `ActionFactory`, placed before or after `_execute_with_retry`):
```python
def _resolve_locator(self, locator: LocatorDefinition) -> LocatorDefinition:
    """Return a locator with any ``${param}`` tokens in its value expanded.

    When ``self._params`` is empty or the locator value contains no tokens,
    returns *locator* unchanged (zero allocation).
    """
    if not self._params:
        return locator
    from src.actions.value_resolver import resolve_locator_params
    resolved_value = resolve_locator_params(locator.value, self._params)
    if resolved_value == locator.value:
        return locator  # no tokens — reuse original
    return LocatorDefinition(by=locator.by, value=resolved_value)
```

**Modified `run()` method** — the `LocatorDefinition` import must be added at the top of the file (or rely on the deferred import inside `_resolve_locator`). The seam is option (b): resolve the locator UPSTREAM, build a resolved `ElementDefinition` copy via `model_copy`, and pass that copy (`target`) consistently to the probe, retry, and executor. `ElementActions.execute` reads `element.locator` internally at ~9 branches and takes no separate locator arg, so the resolved locator MUST travel inside `target`, not as a local variable. The `run()` body change (lines 43-61):
```python
def run(self, element: ElementDefinition) -> None:
    resolved_locator = self._resolve_locator(element.locator)  # ADD: Phase 21
    target = (
        element
        if resolved_locator is element.locator
        else element.model_copy(update={"locator": resolved_locator})
    )

    if element.options and element.options.get("skip_if_not_visible"):
        if not self._page.is_visible(target.locator):           # CHANGE: was element.locator
            logger.info(
                "[%s] Not visible — skipping (skip_if_not_visible=true)", element.name
            )
            raise SkipElementSignal(element.name)

    resolved_value = self._resolver.resolve(element.value)        # ORIGINAL element value (anchored, D-03)

    # 1. Pre-wait
    if element.pre_wait:
        logger.debug("[%s] Executing pre_wait: %s", element.name, element.pre_wait.condition.value)
        self._wm.wait_for_condition(element.pre_wait, element_name=element.name)

    # 2. Action (with optional retry on retryable elements)
    if element.retryable and element.retry_count > 0:
        self._execute_with_retry(target, resolved_value)         # CHANGE: target carries resolved locator
    else:
        self._executor.execute(target, resolved_value)           # CHANGE: target carries resolved locator

    # 3. Post-wait
    if element.post_wait:
        logger.debug("[%s] Executing post_wait: %s", element.name, element.post_wait.condition.value)
        self._wm.wait_for_condition(element.post_wait, element_name=element.name)
```

**Note on `_executor.execute`:** `ElementActions.execute(target, resolved_value)` reads `target.locator` internally at every dispatch branch. Because `target` is the resolved copy (or the original when no tokens are present), the resolved locator reaches every branch without modifying `ElementActions`. Do NOT pass a separate `resolved_locator` argument — `execute` has no such parameter under option (b).

**`LocatorDefinition` import** — must be added if not already present:
```python
from src.models.workflow_models import ElementDefinition, LocatorDefinition
```
(Currently only `ElementDefinition` is imported — see line 9: `from src.models.workflow_models import ElementDefinition`)

**ValueError propagation path** (verified from workflow_engine.py lines 166-174):
```python
except Exception as exc:
    ...
    self._collector.record_fail(
        ctx, element.action, f"Unexpected: {exc}",
        failure_phase=FailurePhase.ACTION,
        ...
    )
```
A `ValueError` raised by `resolve_locator_params` propagates through `_resolve_locator` → `run()` → the `except Exception` block in `WorkflowEngine._run_element` and is recorded as FAILED with `f"Unexpected: Unknown locator param '${x}'..."`.

---

### `tests/unit/test_value_resolver.py` (test, transform)

**Analog:** `tests/unit/test_value_resolver.py` — existing `TestParamExpansion` class (lines 302-387).

**Imports pattern** (lines 1-19) — unchanged; add `resolve_locator_params` to the import block:
```python
from src.actions.value_resolver import (
    PLACEHOLDER_REGISTRY,
    ValueResolver,
    configure_env_resolver,
    generate_first_name,
    generate_last_day_of_next_month,
    generate_last_name,
    generate_sin_number,
    resolve_dynamic_value,
    resolve_locator_params,   # ADD for Phase 21
)
```

**New test class to ADD** — mirrors `TestParamExpansion` structure, using test IDs LP-01..LP-05 in docstrings:
```python
# ---------------------------------------------------------------------------
# Phase 21 — LP-01..LP-05: resolve_locator_params() non-anchored expansion
# ---------------------------------------------------------------------------

class TestResolveLocatorParams:
    """LP-01..LP-05: Non-anchored partial expansion for locator selector strings."""

    # LP-01
    def test_embedded_token_xpath(self):
        result = resolve_locator_params("//div[@id='${company_code}']", {"company_code": "ACME"})
        assert result == "//div[@id='ACME']"

    # LP-02
    def test_embedded_token_css(self):
        result = resolve_locator_params("#row-${id}", {"id": "42"})
        assert result == "#row-42"

    # LP-03
    def test_multiple_tokens_expanded(self):
        result = resolve_locator_params(
            "//div[@id='${a}']/span[@class='${b}']",
            {"a": "foo", "b": "bar"},
        )
        assert result == "//div[@id='foo']/span[@class='bar']"

    # LP-04
    def test_no_token_returns_unchanged(self):
        result = resolve_locator_params("//div[@class='static']", {})
        assert result == "//div[@class='static']"

    # LP-05
    def test_unknown_token_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown locator param"):
            resolve_locator_params("//div[@id='${missing}']", {})

    def test_full_value_token_also_works(self):
        # Single full-value token is a subset of embedded — must still expand
        result = resolve_locator_params("${company_code}", {"company_code": "ACME"})
        assert result == "ACME"

    def test_partial_token_raises_not_silently_skips(self):
        # An unknown token embedded in a longer string must raise, not pass through
        with pytest.raises(ValueError, match="Unknown locator param"):
            resolve_locator_params(".class_${type}_box", {})

    def test_error_message_lists_available_params(self):
        with pytest.raises(ValueError) as exc_info:
            resolve_locator_params("${x}", {"a": "1", "b": "2"})
        msg = str(exc_info.value)
        assert "Workflow params:" in msg
        assert "'a'" in msg
```

**Pattern: error assertion** (mirrors VP-02 at line 311-316):
```python
with pytest.raises(ValueError) as exc_info:
    resolve_dynamic_value("${account_type}", params={})
msg = str(exc_info.value)
assert "Unknown placeholder" in msg
assert "Workflow params:" in msg
```

---

### `tests/unit/test_locator_resolver.py` (test, transform)

**Analog:** `tests/unit/test_locator_resolver.py` — existing `TestLocatorResolver` class (lines 12-68).

**Seam reminder:** Under option (b) the locator is resolved UPSTREAM in `ActionFactory`, NOT inside `LocatorResolver.resolve`. `LocatorResolver.resolve` is unchanged and has NO `params` kwarg. Therefore the new test class exercises the seam through `ActionFactory` (its `_resolve_locator` helper and the resolved `ElementDefinition` copy), never via `LocatorResolver.resolve(locator, params=...)`.

**Imports pattern** — `LocatorResolver` is still imported (the existing `TestLocatorResolver` class uses it). The new class additionally needs `ActionFactory`, `ElementDefinition`, and `MagicMock`:
```python
"""Unit tests for LocatorResolver and ActionFactory locator-param resolution — no browser required."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from selenium.webdriver.common.by import By

from src.actions.action_factory import ActionFactory
from src.core.exceptions import LocatorResolutionError
from src.locators.locator_resolver import LocatorResolver
from src.models.workflow_models import ElementDefinition, LocatorDefinition
```

**Existing test class pattern** — `TestLocatorResolver` (lines 12-68) uses direct `LocatorDefinition` construction, no fixtures, calls `LocatorResolver.resolve(locator)` or `LocatorResolver.resolve(locator, element_name="x")`. It is unchanged (regression coverage that `LocatorResolver.resolve` still returns the raw value with no params kwarg).

**New test class to ADD** — exercises the option-(b) seam through `ActionFactory`, using LP-06..LP-09 IDs. Construct an `ActionFactory` with `MagicMock` page/wait_manager and a `params` dict, then assert `_resolve_locator(...)` returns the resolved `LocatorDefinition` (or the original instance when there are no tokens / no params):
```python
class TestLocatorResolverWithParams:
    """LP-06..LP-09: ActionFactory resolves ${param} tokens in locator values upstream (option b)."""

    @staticmethod
    def _factory(params):
        # MagicMock page/wait_manager — no browser; we only exercise _resolve_locator.
        return ActionFactory(page=MagicMock(), wait_manager=MagicMock(), params=params)

    # LP-06
    def test_resolve_full_value_token(self):
        factory = self._factory({"company_code": "ACME"})
        locator = LocatorDefinition(by="id", value="${company_code}")
        resolved = factory._resolve_locator(locator)
        assert resolved.by == "id"
        assert resolved.value == "ACME"

    def test_resolve_embedded_xpath_token(self):
        factory = self._factory({"company_code": "ACME"})
        locator = LocatorDefinition(by="xpath", value="//div[@id='${company_code}']")
        resolved = factory._resolve_locator(locator)
        assert resolved.value == "//div[@id='ACME']"

    def test_resolve_embedded_css_token(self):
        factory = self._factory({"id": "42"})
        locator = LocatorDefinition(by="css_selector", value="#row-${id}")
        resolved = factory._resolve_locator(locator)
        assert resolved.value == "#row-42"

    # LP-07: no params — original instance returned unchanged (identity, zero allocation)
    def test_no_params_returns_same_instance(self):
        factory = self._factory({})
        locator = LocatorDefinition(by="id", value="${company_code}")
        resolved = factory._resolve_locator(locator)
        assert resolved is locator   # identity — no expansion, raw value preserved

    def test_no_token_with_params_returns_same_instance(self):
        factory = self._factory({"x": "y"})
        locator = LocatorDefinition(by="css_selector", value="//div[@class='static']")
        resolved = factory._resolve_locator(locator)
        assert resolved is locator   # no tokens — reuse original

    # LP-08: unknown token fails loud (D-05)
    def test_unknown_token_raises_value_error(self):
        factory = self._factory({"other": "v"})
        locator = LocatorDefinition(by="css_selector", value="#row-${missing}")
        with pytest.raises(ValueError, match="Unknown locator param"):
            factory._resolve_locator(locator)

    # LP-09: run() threads the resolved ElementDefinition copy through to execute()
    def test_run_passes_resolved_locator_to_executor(self):
        factory = self._factory({"company_code": "ACME"})
        # CLICK action so element-value resolution does not interfere.
        element = ElementDefinition(
            name="login",
            action="click",
            locator=LocatorDefinition(by="id", value="${company_code}"),
        )
        factory._executor = MagicMock()
        factory.run(element)
        passed_element = factory._executor.execute.call_args.args[0]
        assert passed_element.locator.value == "ACME"   # resolved copy, not the raw ${company_code}
```

---

## Shared Patterns

### `params or {}` storage convention
**Source:** `src/actions/value_resolver.py` line 228 (`ValueResolver.__init__`)
**Apply to:** `ActionFactory.__init__` — the new `self._params` assignment must use the same convention.
```python
self._params: dict = params or {}
```

### ValueError / fail-loud on unknown token
**Source:** `src/actions/value_resolver.py` lines 203-207 (`resolve_dynamic_value`)
**Apply to:** `resolve_locator_params` in `value_resolver.py`
```python
raise ValueError(
    f"Unknown placeholder '${{{key}}}'. "
    f"Registered keys: {sorted(PLACEHOLDER_REGISTRY)}"
    + (f". Workflow params: {sorted(params)}" if params is not None else "")
)
```
New locator error shape (parallel structure):
```python
raise ValueError(
    f"Unknown locator param '${{key}}'. "
    f"Workflow params: {sorted(params)}"
)
```

### from `__future__ import annotations` header
**Source:** All source files in `src/` (e.g. `value_resolver.py` line 1, `locator_resolver.py` line 1, `action_factory.py` line 1)
**Apply to:** All modified files — retain this header unchanged.

### Test class docstring with phase-ID prefix
**Source:** `tests/unit/test_value_resolver.py` line 303
**Apply to:** All new test classes
```python
class TestParamExpansion:
    """VP-01..VP-10: Workflow parameter names resolve as ${param_name} in element values."""
```
New classes follow the same convention:
```python
class TestResolveLocatorParams:
    """LP-01..LP-05: Non-anchored partial expansion for locator selector strings."""

class TestLocatorResolverWithParams:
    """LP-06..LP-09: ActionFactory resolves ${param} tokens in locator values upstream (option b)."""
```

### `pytest.raises(ValueError, match=...)` error assertion pattern
**Source:** `tests/unit/test_value_resolver.py` lines 127-128 and 311-316
**Apply to:** All unknown-token error tests in new test classes
```python
with pytest.raises(ValueError, match="Unknown placeholder"):
    resolve_dynamic_value("${nonexistent_key}")
```

---

## No Analog Found

No files in this phase lack an analog. All four touch points have strong existing patterns in the codebase.

---

## Critical Anti-Patterns (do not copy)

| Anti-pattern | Source | Why it fails |
|---|---|---|
| Reusing `_PLACEHOLDER_PATTERN` for locator expansion | `value_resolver.py:15` | Anchored `^\$\{…\}$` returns `None` for embedded tokens; locator `//div[@id='${x}']` would pass through unexpanded |
| Calling `resolve_dynamic_value()` for locator expansion | `value_resolver.py:157` | Same anchored semantics; VP-09 test proves `"prefix_${name}"` is returned unchanged |
| Adding a `params` kwarg to `LocatorResolver.resolve` | `locator_resolver.py:27` | This phase uses option (b) — resolution happens UPSTREAM in ActionFactory. A `params` kwarg on `LocatorResolver.resolve` would not reach the ~9 internal `element.locator` reads inside `ElementActions.execute` without threading params through `execute()`. Do NOT add this kwarg; test the seam via ActionFactory instead. |
| Resolving into a local `resolved_locator` variable only | `action_factory.py:run` | `ElementActions.execute` reads `element.locator` internally; a local variable never reaches it. Build a resolved `ElementDefinition` copy (`model_copy`) and pass `target` everywhere. |
| Mutating `element.locator.value` in place | `workflow_models.py:10` | `LocatorDefinition` is a Pydantic v2 model; construct a new instance instead |
| Gating on `if params:` instead of `if params is not None:` at resolver level | `value_resolver.py:201` | `params={}` with a `${x}` locator must still raise `ValueError` (D-05), not silently skip |

---

## Metadata

**Analog search scope:** `src/actions/`, `src/locators/`, `src/models/`, `src/workflow/`, `tests/unit/`
**Files read:** 7 (`value_resolver.py`, `locator_resolver.py`, `action_factory.py`, `workflow_engine.py`, `workflow_models.py`, `test_value_resolver.py`, `test_locator_resolver.py`)
**Pattern extraction date:** 2026-06-09
