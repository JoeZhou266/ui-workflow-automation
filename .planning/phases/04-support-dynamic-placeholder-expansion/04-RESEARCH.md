# Phase 4: Support Dynamic Placeholder Expansion — Research

**Researched:** 2026-05-19
**Domain:** Python value resolution / data generation / JSON workflow loader
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SC-1 | A `PLACEHOLDER_REGISTRY` maps token names to generator functions | Dictionary constant in `src/actions/value_resolver.py`; pattern follows existing module structure |
| SC-2 | `resolve_dynamic_value()` detects `${placeholder}` patterns and calls the registered generator | `re.fullmatch` on `r'\${([^}]+)}'`; lives in `value_resolver.py` alongside `ValueResolver` |
| SC-3 | `JsonLoader` passes every element value through `resolve_dynamic_value()` | Integration point is `ValueResolver._resolve_string()` — already called by `ActionFactory` for every element before dispatch |
| SC-4 | `generate_sin_number()` returns a valid random Canadian SIN | Luhn mod-10 algorithm verified against Wikipedia canonical example; first digit 1–8; zero external dependencies |
| SC-5 | `generate_first_name()` and `generate_last_name()` return random names | Static curated lists + `random.choice()`; zero external dependencies; no Faker needed |
| SC-6 | Unit tests cover resolution, passthrough (no placeholder), and unknown placeholder behavior | New `TestPlaceholderRegistry` class in `tests/unit/test_value_resolver.py`; follows `TestValueResolver` convention in `test_action_dispatch.py` |
</phase_requirements>

---

## Summary

Phase 4 adds a registry-based placeholder expansion feature to the existing `ValueResolver` class in `src/actions/value_resolver.py`. When a workflow JSON element `value` field contains a token like `${sin_number}`, the framework calls the registered generator function instead of using the literal string.

The existing architecture already has the correct integration hook. `ActionFactory.run()` calls `_resolver.resolve(element.value)` for every element before dispatch (line 42 of `action_factory.py`). `ValueResolver._resolve_string()` is already the stub extension point — its docstring explicitly says "add `${variable}` substitution here when needed." The entire feature can be delivered by filling in that stub plus adding generator functions, without touching any other file.

The Canadian SIN generator requires a pure-Python Luhn mod-10 implementation. No external packages are needed anywhere in Phase 4. The stdlib `random` module covers both name selection (via `random.choice` from static lists) and SIN digit generation (via `random.randint`). The project's `requirements.txt` does not include Faker or any name-generation library, and installing one is not required.

**Primary recommendation:** Implement `PLACEHOLDER_REGISTRY`, `resolve_dynamic_value()`, and generator functions inside `src/actions/value_resolver.py`. Wire the call inside `ValueResolver._resolve_string()`. Write tests in `tests/unit/test_value_resolver.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Placeholder token detection | Action layer (`src/actions/`) | — | `ValueResolver` is already the value-processing extension point used by `ActionFactory` |
| Generator registry | Action layer (`src/actions/`) | — | Co-located with `ValueResolver` in `value_resolver.py`; no cross-layer dependency needed |
| SIN generation | Action layer (`src/actions/`) | — | Pure computation, no I/O or browser involvement |
| Name generation | Action layer (`src/actions/`) | — | Pure computation, static list |
| JSON loading integration | No change required | — | `ActionFactory` already calls `ValueResolver.resolve()` before every dispatch — the hook is already wired |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `re` (stdlib) | Python 3.9 built-in | Regex pattern matching for `${...}` tokens | Zero-dependency; sufficient for single-token detection |
| `random` (stdlib) | Python 3.9 built-in | `randint` for SIN digits; `choice` for name lists | Zero-dependency; already used elsewhere in Python ecosystem |

### No New Dependencies Required

The entire feature uses only Python stdlib. The project `requirements.txt` does not include Faker, `names`, or any name-generation library — and none is needed.

**Installation:** None. No `pip install` required for this phase.

**Version verification:** `[VERIFIED: local pip list]` — `faker` and `names` packages are NOT installed. No package found in `requirements.txt` for name generation.

---

## Architecture Patterns

### System Architecture Diagram

```
Workflow JSON element.value (string)
           |
           v
   ActionFactory.run(element)
           |
           v
   ValueResolver.resolve(value)          <-- existing call at action_factory.py:42
           |
           v
   ValueResolver._resolve_string(value)  <-- FILL THIS STUB IN
           |
     contains ${...}?
          /      \
        YES       NO
         |         |
         v         v
  resolve_dynamic_value(value)   return original value unchanged
         |
   match = re.fullmatch(PATTERN, value)
         |
     match found?
        /      \
      YES        NO
       |          |
       v          v
  key = match.group(1)    return original value unchanged
       |
   key in PLACEHOLDER_REGISTRY?
        /         \
      YES          NO
       |            |
       v            v
  call generator()  raise ValueError("Unknown placeholder: ${key}")
       |
       v
  return generated string
```

### Recommended Project Structure

No new directories needed. All new code lands in existing files or a new peer file:

```
src/
└── actions/
    ├── value_resolver.py      # EXPAND: add PLACEHOLDER_REGISTRY, resolve_dynamic_value(), generators
    └── action_factory.py      # NO CHANGE — already calls ValueResolver.resolve()

tests/
└── unit/
    └── test_value_resolver.py  # NEW: focused tests for placeholder resolution
```

### Pattern 1: Registry + Function Dispatch

**What:** A module-level dict maps string keys to zero-argument callables. `resolve_dynamic_value()` looks up the key and calls the callable.

**When to use:** When the set of tokens is closed and known at code-write time. For open-ended extensibility, a registration API could be added later, but for this phase a simple dict is sufficient and matches the user spec.

**Example:**
```python
# Source: user spec (project/Support-dynamic-placeholder-expansion.md)
from __future__ import annotations
import re
import random
from typing import Callable, Dict

_PATTERN = re.compile(r'^\$\{([^}]+)\}$')

PLACEHOLDER_REGISTRY: Dict[str, Callable[[], str]] = {
    "sin_number": generate_sin_number,
    "first_name": generate_first_name,
    "last_name":  generate_last_name,
}

def resolve_dynamic_value(value: str) -> str:
    match = _PATTERN.match(value)
    if not match:
        return value
    key = match.group(1)
    if key not in PLACEHOLDER_REGISTRY:
        raise ValueError(f"Unknown placeholder: ${{{key}}}")
    return PLACEHOLDER_REGISTRY[key]()
```

### Pattern 2: Canadian SIN via Luhn Mod-10

**What:** Generate 8 random digits (first digit 1–8), compute the Luhn check digit, append it to form a 9-digit string.

**When to use:** Every call to `generate_sin_number()`.

**Luhn check-digit derivation (verified):**

Position numbering is 0-indexed from the left across the 8 prefix digits. Digits at even positions (0, 2, 4, 6) are kept as-is; digits at odd positions (1, 3, 5, 7) are doubled. If doubling yields ≥ 10, subtract 9. Sum all values. Check digit = `(10 - (total % 10)) % 10`.

Wikipedia canonical example `046-454-286`: prefix `04645428` → sum 44 → check digit 6 → `046454286`, total sum 50, divisible by 10. `[VERIFIED: manual computation against Wikipedia SIN article]`

**Example:**
```python
# Source: [VERIFIED: manual Luhn verification against Wikipedia SIN example]
def generate_sin_number() -> str:
    """Return a 9-digit string that is a mathematically valid Canadian SIN."""
    first = random.randint(1, 8)           # province codes 1-8; 0=CRA, 9=temporary
    rest  = [random.randint(0, 9) for _ in range(7)]
    digits_8 = [first] + rest
    total = 0
    for i, d in enumerate(digits_8):
        if i % 2 == 1:                     # odd-indexed from left: double
            doubled = d * 2
            total += doubled if doubled < 10 else doubled - 9
        else:
            total += d
    check = (10 - (total % 10)) % 10
    return "".join(str(d) for d in digits_8 + [check])
```

### Pattern 3: Static Name Lists

**What:** `random.choice()` over a curated list of common first/last names.

**When to use:** Every call to `generate_first_name()` / `generate_last_name()`.

The lists should be long enough to avoid obvious repetition in test runs but do not need to be exhaustive. 30–40 entries per list is sufficient. The lists are internal constants in `value_resolver.py`.

```python
# Source: [ASSUMED] standard English first/last names — no library needed
_FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Emma", "Liam", "Olivia", "Noah", "Ava", "Sophia",
    "Mason", "Isabella", "Ethan", "Mia", "Lucas", "Charlotte",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
]

def generate_first_name() -> str:
    return random.choice(_FIRST_NAMES)

def generate_last_name() -> str:
    return random.choice(_LAST_NAMES)
```

### Anti-Patterns to Avoid

- **Anti-pattern — Modifying `json_loader.py` or `WorkflowLoader`:** The spec says "JsonLoader passes every element value through `resolve_dynamic_value()`" but the correct interpretation is that `ValueResolver` (called by `ActionFactory`) is the integration point. Modifying `json_loader.py` would resolve placeholders before Pydantic validation, which can cause validation errors if a generated SIN is type-checked too strictly. Resolution at action-dispatch time (current `ValueResolver` call site) is architecturally correct. `[VERIFIED: tracing call chain in action_factory.py:42]`
- **Anti-pattern — Caching generated values:** Each call to a generator should be independent. If the same `${sin_number}` appears in two elements, they should receive different generated values. The registry must store callables, not pre-computed strings.
- **Anti-pattern — Partial-match expansion (string substitution):** If `resolve_dynamic_value("Hello ${name}")` tried to do string replacement, it would produce values like `"Hello Smith"` which break expected Selenium input strings. The spec implies full-token replacement: value is entirely a placeholder or it is left unchanged. Use `re.fullmatch` (or `^...$` anchors), not `re.sub`.
- **Anti-pattern — Adding Faker as a dependency:** Faker is not in `requirements.txt`. Adding it is unnecessary (static lists suffice) and increases install size and boot time.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Luhn check-digit computation | Nothing — this must be custom | Stdlib `random` + custom 5-line algorithm | No Python stdlib or PyPI package dedicated to SIN generation; Luhn is simple enough to implement correctly in <10 lines |
| Name lists | Elaborate locale-aware name DB | Static 30-item list + `random.choice` | Sufficient randomness for test data; zero risk of external dependency breakage |
| Token regex | Hand-written state machine | `re.compile(r'^\$\{([^}]+)\}$')` | One-liner; stdlib; already used in pattern throughout Python ecosystem |

---

## Common Pitfalls

### Pitfall 1: Wrong Luhn Doubling Direction

**What goes wrong:** Implementing the doubling from the right (rightmost digit = check digit, then every second from there) instead of from the left of the 8-digit prefix. Both approaches can produce valid SINs, but they must be internally consistent — the validator must use the same convention as the generator.

**Why it happens:** Wikipedia describes Luhn "from the rightmost digit" but for generation, we work left-to-right on the prefix.

**How to avoid:** Generate 8 prefix digits, double positions 1, 3, 5, 7 (0-indexed from left), compute check digit, then append. The test verifies the 9-digit result by running Luhn validation end-to-end.

**Warning signs:** `luhn_validate(generate_sin_number())` returns `False` in tests.

### Pitfall 2: First Digit Includes 0 or 9

**What goes wrong:** `random.randint(0, 9)` for the first digit produces SINs starting with 0 (CRA-specific numbers) or 9 (temporary resident SINs). These are technically valid Luhn numbers but not standard Canadian SINs.

**Why it happens:** Naive use of `randint(0, 9)`.

**How to avoid:** Use `random.randint(1, 8)` for the first digit only.

**Warning signs:** Generated SINs occasionally start with `0` or `9`.

### Pitfall 3: Regex Matches Partial Tokens

**What goes wrong:** Using `re.search` or `re.sub` instead of `re.fullmatch`/`re.match` with anchors. A value like `"SIN: ${sin_number}"` would be partially matched.

**Why it happens:** Default `re.search` finds a match anywhere in the string.

**How to avoid:** Use `re.fullmatch(pattern, value)` — the entire value must be the token. Or equivalently, use `^` and `$` anchors with `re.match`.

**Warning signs:** Unit test with value `"prefix_${sin_number}"` incorrectly generates a SIN instead of returning the original string.

### Pitfall 4: Mutable Module-Level Registry Mutated in Tests

**What goes wrong:** Tests that add to or remove from `PLACEHOLDER_REGISTRY` at module level without cleanup leave state for subsequent tests.

**Why it happens:** `PLACEHOLDER_REGISTRY` is a mutable dict defined at module level.

**How to avoid:** In tests that need to inject a fake generator, use `unittest.mock.patch.dict` to temporarily replace registry entries, which restores state automatically after the test.

**Warning signs:** Tests pass in isolation but fail when run together; order-dependent test failures.

---

## Code Examples

### Full `resolve_dynamic_value` implementation

```python
# Source: derived from user spec and codebase analysis [VERIFIED: integration point confirmed]
from __future__ import annotations

import re
import random
from typing import Any, Callable, Dict, Optional

_PLACEHOLDER_PATTERN = re.compile(r'^\$\{([^}]+)\}$')


def generate_sin_number() -> str:
    """Return a 9-digit string that passes the Canadian SIN Luhn mod-10 check."""
    first = random.randint(1, 8)
    rest = [random.randint(0, 9) for _ in range(7)]
    digits_8 = [first] + rest
    total = 0
    for i, d in enumerate(digits_8):
        if i % 2 == 1:
            doubled = d * 2
            total += doubled if doubled < 10 else doubled - 9
        else:
            total += d
    check = (10 - (total % 10)) % 10
    return "".join(str(d) for d in digits_8 + [check])


_FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer",
    "Michael", "Linda", "William", "Barbara", "David", "Elizabeth",
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Sophia",
    "Mason", "Isabella", "Ethan", "Mia", "Lucas", "Charlotte",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
    "Miller", "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson",
    "Taylor", "Moore", "Jackson", "Lee", "Perez", "Thompson",
    "White", "Harris", "Clark", "Ramirez", "Lewis", "Robinson",
]


def generate_first_name() -> str:
    return random.choice(_FIRST_NAMES)


def generate_last_name() -> str:
    return random.choice(_LAST_NAMES)


PLACEHOLDER_REGISTRY: Dict[str, Callable[[], str]] = {
    "sin_number": generate_sin_number,
    "first_name": generate_first_name,
    "last_name":  generate_last_name,
}


def resolve_dynamic_value(value: str) -> str:
    """Resolve a ``${placeholder}`` token to a generated value.

    If *value* is not a placeholder token, it is returned unchanged.
    Raises ``ValueError`` for unregistered placeholder names.
    """
    match = _PLACEHOLDER_PATTERN.match(value)
    if not match:
        return value
    key = match.group(1)
    if key not in PLACEHOLDER_REGISTRY:
        raise ValueError(
            f"Unknown placeholder '${{{{key}}}}'. "
            f"Registered: {sorted(PLACEHOLDER_REGISTRY)}"
        )
    return PLACEHOLDER_REGISTRY[key]()
```

### Updated `ValueResolver._resolve_string`

```python
# Source: existing src/actions/value_resolver.py stub filled in
def _resolve_string(self, value: str) -> str:
    return resolve_dynamic_value(value)
```

### Luhn validation helper for tests

```python
# Source: [VERIFIED: manually confirmed against Wikipedia SIN 046-454-286]
def _luhn_valid(sin: str) -> bool:
    digits = [int(c) for c in sin]
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            doubled = d * 2
            total += doubled if doubled < 10 else doubled - 9
        else:
            total += d
    return total % 10 == 0
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ValueResolver._resolve_string` returns `value` unchanged (stub) | Calls `resolve_dynamic_value()` from registry | Phase 4 | Enables dynamic test data in JSON workflows |
| Hardcoded test data in workflow JSON | `${placeholder}` tokens resolved at runtime | Phase 4 | Unique generated values per run |

**Deprecated/outdated:**
- The `_resolve_string` stub comment "Extension point: add ${variable} substitution here when needed" is replaced by the actual implementation in this phase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Static first/last name lists (no external library) are sufficient for the phase's randomness requirement | Standard Stack | Low — if richer locale-aware names are needed, Faker can be added later without changing the interface |
| A2 | `resolve_dynamic_value` should raise `ValueError` for unknown placeholders (rather than silently returning the original string) | Architecture Patterns | Low — behavior is covered by a unit test; easy to change if user prefers silent passthrough |
| A3 | Full-token-only matching (no substring substitution) is the intended behavior | Architecture Patterns | Low — spec says "detect patterns like `${placeholder}`" without specifying mixed-string behavior; fullmatch is the safer interpretation |

---

## Open Questions

1. **Multiple placeholders in one value string**
   - What we know: Spec says "Detect patterns like `${placeholder}`" — no mention of multiple tokens in one string.
   - What's unclear: Should `"${first_name} ${last_name}"` resolve to `"Emma Smith"` or be treated as an unknown pattern?
   - Recommendation: Treat full-value-as-token only (fullmatch approach). A value containing two tokens is not a valid placeholder format and is returned unchanged. This is safe and can be extended later.

2. **Thread safety of `PLACEHOLDER_REGISTRY` mutations**
   - What we know: Tests must not mutate the registry permanently; production code never mutates it.
   - What's unclear: Whether future callers will want to add generators at runtime.
   - Recommendation: Keep the dict mutable for now (extensibility); document that test mutations require `unittest.mock.patch.dict`.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — all code is pure Python stdlib; no tools, services, or CLIs are required for this phase).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pytest.ini` (rootdir) |
| Quick run command | `pytest tests/unit/test_value_resolver.py -v` |
| Full suite command | `pytest tests/unit/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SC-1 | `PLACEHOLDER_REGISTRY` is a dict mapping `sin_number`, `first_name`, `last_name` to callables | unit | `pytest tests/unit/test_value_resolver.py::TestPlaceholderRegistry::test_registry_keys_exist -x` | ❌ Wave 0 |
| SC-2 | `resolve_dynamic_value("${sin_number}")` returns a 9-digit string | unit | `pytest tests/unit/test_value_resolver.py::TestPlaceholderRegistry::test_resolve_sin_number -x` | ❌ Wave 0 |
| SC-2 | `resolve_dynamic_value("no placeholder")` returns original string unchanged | unit | `pytest tests/unit/test_value_resolver.py::TestPlaceholderRegistry::test_passthrough_no_placeholder -x` | ❌ Wave 0 |
| SC-2 | `resolve_dynamic_value("prefix_${sin_number}")` returns original string unchanged (no partial match) | unit | `pytest tests/unit/test_value_resolver.py::TestPlaceholderRegistry::test_passthrough_mixed_string -x` | ❌ Wave 0 |
| SC-2 | `resolve_dynamic_value("${unknown_key}")` raises `ValueError` | unit | `pytest tests/unit/test_value_resolver.py::TestPlaceholderRegistry::test_unknown_placeholder_raises -x` | ❌ Wave 0 |
| SC-3 | `ValueResolver.resolve("${sin_number}")` returns a generated SIN (not the literal) | unit | `pytest tests/unit/test_value_resolver.py::TestValueResolverIntegration::test_resolver_expands_sin -x` | ❌ Wave 0 |
| SC-3 | `ValueResolver.resolve(42)` returns `42` unchanged (non-string passthrough) | unit | already in `TestValueResolver` in `test_action_dispatch.py` | ✅ |
| SC-4 | `generate_sin_number()` returns 9 digits | unit | `pytest tests/unit/test_value_resolver.py::TestGenerators::test_sin_length -x` | ❌ Wave 0 |
| SC-4 | `generate_sin_number()` result passes Luhn mod-10 check | unit | `pytest tests/unit/test_value_resolver.py::TestGenerators::test_sin_luhn_valid -x` | ❌ Wave 0 |
| SC-4 | `generate_sin_number()` result starts with digit 1–8 | unit | `pytest tests/unit/test_value_resolver.py::TestGenerators::test_sin_first_digit -x` | ❌ Wave 0 |
| SC-5 | `generate_first_name()` returns a non-empty string | unit | `pytest tests/unit/test_value_resolver.py::TestGenerators::test_first_name_nonempty -x` | ❌ Wave 0 |
| SC-5 | `generate_last_name()` returns a non-empty string | unit | `pytest tests/unit/test_value_resolver.py::TestGenerators::test_last_name_nonempty -x` | ❌ Wave 0 |
| SC-6 | Multiple calls to `generate_sin_number()` produce different values (probabilistic randomness check) | unit | `pytest tests/unit/test_value_resolver.py::TestGenerators::test_sin_randomness -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/test_value_resolver.py -v`
- **Per wave merge:** `pytest tests/unit/ -v`
- **Phase gate:** `pytest tests/unit/ -v` — all 143+ tests green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_value_resolver.py` — new file covering SC-1 through SC-6; must be created before any implementation

*(If no gaps: "None — existing test infrastructure covers all phase requirements")*

---

## Project Constraints (from CLAUDE.md)

All of the following must be honoured during planning and implementation:

| Directive | What it means for Phase 4 |
|-----------|--------------------------|
| Python 3.9.13 | Use `from __future__ import annotations`; no 3.10+ syntax (no `match`/`case`) |
| No `time.sleep()` | Not applicable to this phase (no Selenium interaction) |
| Pydantic v2 installed (`pydantic>=2.0.0`) | Use `model_validate` not `parse_obj`; not directly relevant to Phase 4 |
| Implicit wait must stay 0 | Not applicable to this phase |
| Never hardcode credentials | Not applicable to this phase |
| `from __future__ import annotations` | Required at top of every new `.py` file |
| pytest for tests | Tests go in `tests/unit/` with no browser fixtures |

---

## Security Domain

The feature generates random test data (SIN numbers, names) with no security implications — no authentication, no cryptographic operations, no user input injection surfaces. No ASVS categories apply. `security_enforcement` is not configured in `.planning/config.json` (key absent); however, the threat surface of this phase is nil.

---

## Sources

### Primary (HIGH confidence)
- `[VERIFIED: local codebase inspection]` — `src/actions/value_resolver.py`, `src/actions/action_factory.py` — integration point at `action_factory.py:42`
- `[VERIFIED: local codebase inspection]` — `src/models/workflow_models.py` — `ElementDefinition.value: Optional[Any]` — the field that carries placeholder strings
- `[VERIFIED: manual Luhn computation]` — Wikipedia SIN canonical example `046-454-286` produces Luhn sum 50; check digit derivation formula confirmed correct in Python interpreter
- `[VERIFIED: pip show faker names]` — neither `faker` nor `names` is installed; `requirements.txt` does not list them

### Secondary (MEDIUM confidence)
- `[CITED: https://en.wikipedia.org/wiki/Social_insurance_number]` — SIN structure, first-digit province codes, Luhn algorithm description
- `[CITED: project/Support-dynamic-placeholder-expansion.md]` — user spec defining the registry shape, function names, and requirements

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — codebase verified; no external packages needed
- Architecture: HIGH — integration point confirmed by code tracing; Luhn algorithm verified by computation
- Pitfalls: HIGH — all identified by code tracing; Luhn doubling direction confirmed in interpreter

**Research date:** 2026-05-19
**Valid until:** 2026-07-01 (stable stdlib feature, no expiry risk)
