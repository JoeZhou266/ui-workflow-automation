---
phase: 21-support-locator-value-from-workflow-parameters-e-g-locator-v
reviewed: 2026-06-10T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/actions/value_resolver.py
  - src/actions/action_factory.py
  - tests/unit/test_value_resolver.py
  - tests/unit/test_locator_resolver.py
findings:
  critical: 1
  warning: 5
  info: 4
  total: 10
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-06-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

This phase adds workflow-parameter expansion into `locator.value` strings via a new
non-anchored `resolve_locator_params()` helper and an `ActionFactory._resolve_locator()`
seam (option b). The seam wiring, identity-passthrough optimization, and fail-loud unknown-token
behavior are correctly implemented and well tested for the happy path.

The most serious defect is a **value/locator resolution asymmetry in `run()`**: `resolved_value`
is computed from the *original* `element.value`, not from `target.value`. While today both read
the same value object, the code is now structured around a `target` copy, and this inconsistency
is a latent bug magnet. More substantively, the new locator-param feature performs raw string
substitution into CSS/XPath selectors with **no escaping or quote-safety handling** — a token value
containing a quote produces a malformed or attacker-influenced selector. The test suite actually
encodes the broken-selector behavior (`O'Brien` → unbalanced XPath) as an expected result, which
locks in the defect. Several quality issues (empty-string registry coverage gap, function-local
imports, unused `random_number` test coverage, type-annotation mismatch) round out the findings.

## Critical Issues

### CR-01: Locator param substitution is unescaped — quote/selector injection and malformed selectors

**File:** `src/actions/value_resolver.py:249-258` (with test at `tests/unit/test_value_resolver.py:439-442`)

**Issue:** `resolve_locator_params()` performs raw `str.replace`-style substitution of param
values directly into CSS/XPath selector strings with **no escaping**. When a param value contains
a character that is significant to the selector grammar (single quote, double quote, `]`, `>`,
backslash), the resulting selector is either malformed or semantically altered.

The test `test_xpath_quote_context_preserved` (line 439) explicitly asserts:

```python
result = resolve_locator_params("//div[@title='${label}']", {"label": "O'Brien"})
assert result == "//div[@title='O'Brien']"
```

`//div[@title='O'Brien']` is **not a valid XPath** — the embedded `'` terminates the string literal
and Selenium will raise `InvalidSelectorException` at runtime. The test name claims the quote is
"preserved verbatim", but verbatim preservation here produces a broken selector. This is a
correctness bug being codified as intended behavior.

Because workflow params can originate from external/untrusted sources (env config, CLI, data files),
a value such as `'] | //input[@type='password'][@name='` would let a param value rewrite the selector
to target unintended elements — a selector-injection class of bug analogous to SQL injection.

**Fix:** Do not substitute raw values into selector grammar. Either (a) escape per locator strategy,
or (b) restrict allowed param-value characters and reject otherwise. For XPath, build a safe literal
with `concat()` when the value contains quotes; for CSS, use `CSS.escape`-equivalent escaping. Minimal
hardening:

```python
def _replace(match: re.Match) -> str:
    key = match.group(1)
    if key not in params:
        raise ValueError(
            f"Unknown locator param '${{{key}}}'. Workflow params: {sorted(params)}"
        )
    raw = str(params[key])
    # Reject characters that can break out of / inject into the selector grammar.
    if any(c in raw for c in ("'", '"', "\\")):
        raise ValueError(
            f"Locator param '{key}' value contains unsafe selector character(s); "
            f"refusing to substitute (potential selector injection)."
        )
    return raw
```

Then change the `O'Brien` test to assert a `ValueError` (or to assert proper XPath `concat()`
escaping), rather than asserting the malformed string.

## Warnings

### WR-01: `resolved_value` resolves the original `element.value`, not `target.value`

**File:** `src/actions/action_factory.py:87`

**Issue:** After computing `target` (the locator-resolved copy), the code resolves the element value
from the **original** `element`:

```python
resolved_value = self._resolver.resolve(element.value)
```

while every other downstream use switched to `target` (pre_wait, execute, retry, post_wait). Today
`element.value` and `target.value` reference the same object because `model_copy` only updates
`locator`, so behavior is currently correct. But the function is now organized so that `target` is
the single source of truth for the element being acted on; reading `element.value` here is an
inconsistency that will silently break if a future change makes `target` diverge in `value`. It also
forces a reader to prove the equivalence to trust the code.

**Fix:** Resolve from `target` for consistency:

```python
resolved_value = self._resolver.resolve(target.value)
```

### WR-02: No test covers a param value that breaks the selector being rejected/escaped

**File:** `tests/unit/test_value_resolver.py:438-442`

**Issue:** The only test exercising special characters in a locator value (`O'Brien`) asserts the
malformed output is fine (see CR-01). There is no test asserting that a quote/bracket-bearing param
value is escaped or rejected, so the dangerous behavior is untested-as-dangerous and treated as
correct. This is a test-quality defect that actively masks CR-01.

**Fix:** After fixing CR-01, add tests asserting unsafe values raise `ValueError` (or produce a valid
escaped selector), e.g. values containing `'`, `"`, `]`, `\\`.

### WR-03: `resolve_locator_params` does not validate `value` is a `str`

**File:** `src/actions/value_resolver.py:219`

**Issue:** Unlike `resolve_dynamic_value` (which raises `TypeError` for non-str — lines 192-195),
`resolve_locator_params` calls `_LOCATOR_PARAM_PATTERN.sub(...)` directly on `value` with no type
guard. If a non-str is passed, it raises an opaque `re`-level `TypeError` rather than a clear domain
error. The `ActionFactory._resolve_locator` guard (line 44) protects the production path, but the
public function is documented as taking the raw `locator.value` and is independently importable/tested,
so it should guard its own contract.

**Fix:** Add an explicit type check mirroring `resolve_dynamic_value`:

```python
if not isinstance(value, str):
    raise TypeError(
        f"resolve_locator_params expects a str, got {type(value).__name__!r}"
    )
```

### WR-04: Module-global SIN state makes tests order-dependent and concurrency-unsafe

**File:** `src/actions/value_resolver.py:51-54, 109-118`

**Issue:** `_sin_state` is module-global mutable state shared across all callers. `generate_sin_number`
returns the *next* 3-digit chunk based on `call_count`, so the value returned depends on prior calls
anywhere in the process. The tests assemble full SINs by calling the function exactly three times in
sequence (e.g. `test_resolve_sin_number`, `test_resolver_expands_sin`), which works only as long as no
other test interleaves a single `${sin_number}` call and leaves `call_count` at a non-multiple-of-3.
`test_registry_priority_over_params` (line 322) calls it once and asserts a 3-digit chunk, advancing
the shared counter; if pytest reorders or parallelizes (`pytest-xdist`), the "assemble 3 chunks"
tests can silently assemble chunks from two different SINs and still pass length/`isdigit` assertions
while producing a non-Luhn-valid SIN. The Luhn test (`test_sin_luhn_valid`) is the only guard and it
relies on starting cleanly aligned.

**Fix:** Reset `_sin_state` between tests via a fixture/autouse reset, and/or make the assembling tests
force a fresh SIN (call until `call_count == 0`). Longer term, consider encapsulating SIN state in an
object rather than module globals to remove cross-test coupling.

### WR-05: `random_number` placeholder is registered but has no test coverage and an annotation mismatch

**File:** `src/actions/value_resolver.py:43-45, 162`; tests in `tests/unit/test_value_resolver.py`

**Issue:** `random_number` is added to `PLACEHOLDER_REGISTRY` (line 162) but no test in
`test_value_resolver.py` resolves `${random_number}` or checks its output (length/digit-ness). Every
other registry key has coverage. Additionally, `generate_random_number(length=7)` is stored in a
registry typed `Dict[str, Callable[[], str]]` (line 157) — the registered callable does not match the
zero-arg signature the type promises. It works only because `length` has a default; the type
annotation is misleading and a future caller passing it positionally through the registry contract
would be surprised.

**Fix:** Add a test asserting `${random_number}` resolves to a 7-digit numeric string, and wrap the
generator to match the declared signature, e.g. register `lambda: generate_random_number()` or
annotate the registry to reflect the optional parameter.

## Info

### IN-01: Function-local import of `resolve_locator_params`

**File:** `src/actions/action_factory.py:46`

**Issue:** `resolve_locator_params` is imported inside `_resolve_locator` rather than at module top
(`value_resolver` is already imported at line 6 for `ValueResolver`). There is no circular-import
reason for the deferral, so this is inconsistent with the existing top-level import from the same
module.

**Fix:** Move `from src.actions.value_resolver import resolve_locator_params` to the top-level import
block alongside `ValueResolver`.

### IN-02: Empty-string passes through both resolvers but only one path is tested

**File:** `src/actions/value_resolver.py:219-258`; `tests/unit/test_value_resolver.py:115-116`

**Issue:** `test_passthrough_empty_string` covers `resolve_dynamic_value("")`, but there is no
equivalent test that `resolve_locator_params("", params)` returns `""` (it does, since the regex
finds no match). A minor coverage gap on a boundary input for the new function.

**Fix:** Add `assert resolve_locator_params("", {}) == ""`.

### IN-03: Duplicated Luhn logic between source and test

**File:** `src/actions/value_resolver.py:82-89` and `tests/unit/test_value_resolver.py:27-37`

**Issue:** The Luhn checksum loop is duplicated in `_generate_sin_full` and the test helper
`_luhn_valid`. This is acceptable for a test oracle (independent re-implementation), but worth noting
as duplication if the algorithm ever changes — both copies must stay in sync.

**Fix:** None required; documenting the intentional duplication. If desired, the test could import and
verify against a single shared checksum helper while keeping an independent assertion of the result.

### IN-04: `LocatorResolver` param tests live in `test_locator_resolver.py` but exercise `ActionFactory`

**File:** `tests/unit/test_locator_resolver.py:78-170`

**Issue:** `TestLocatorResolverWithParams` is filed under the LocatorResolver test module but actually
tests `ActionFactory._resolve_locator` (it imports `ActionFactory`, not new `LocatorResolver`
behavior). The docstring acknowledges this ("seam is option (b)"). This misplacement makes the
ActionFactory locator-seam coverage hard to find and conflates two units' tests.

**Fix:** Consider moving these cases into an `ActionFactory`-focused test module (or rename the class to
make the seam ownership obvious) so coverage maps to the unit under test.

---

_Reviewed: 2026-06-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
