# Phase 16: Support Logical Operators (&& / ||) in Conditional $ref — Research

**Researched:** 2026-05-31
**Domain:** Python condition parser extension (stdlib `re`, pure logic)
**Confidence:** HIGH

---

## Summary

Phase 16 extends `src/data/condition_evaluator.py` — the single-file evaluator introduced in Phase 11 — to support compound conditions joined by `&&` (AND) and `||` (OR) logical operators. The existing `evaluate_condition()` signature, error types, and call sites do not change; the function becomes polymorphic over single and compound inputs.

The implementation is a pure Python stdlib task: no new dependencies, no schema changes, no model changes. The entire change is confined to `condition_evaluator.py` and the companion test class `TestEvaluateCondition` in `tests/unit/test_workflow_params.py`.

The key design decision — verified by prototyping against the live codebase — is a two-pass evaluation strategy: split on `&&`/`||` tokens using `re.split`, evaluate each atomic condition with the existing `ATOM_PATTERN`, then reduce with `&&`-before-`||` operator precedence. This approach is backwards-compatible: a string with no `&&` or `||` tokens falls through identically to the current single-atom path.

**Primary recommendation:** Extend `condition_evaluator.py` with a token-split two-pass evaluator; add ~12 new unit tests to `TestEvaluateCondition`; touch no other files.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Compound condition parsing | Data layer (`src/data/`) | — | Load-time concern; no runtime/browser involvement |
| Operator precedence evaluation | Data layer (`src/data/`) | — | Pure logic over resolved string values |
| Error reporting for malformed conditions | Data layer → Core exceptions | — | `WorkflowValidationError` already used by Phase 11 |
| Call site in $ref resolution | Data layer (`src/data/json_loader.py`) | — | Already calls `evaluate_condition()` unchanged |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `re` (stdlib) | Python 3.9.13 built-in | Token-split compound condition string | No external dep; `re.compile` + `re.split` sufficient for flat token grammar |
| `pytest` | 8.4.2 [VERIFIED: `pip show pytest`] | Unit tests | Already the project test runner |
| `pydantic` | 2.13.3 [VERIFIED: `pip show pydantic`] | Not modified in this phase | Existing model unchanged |

### Supporting
None — this phase uses only stdlib and project internals already in place.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `re.split` token approach | Full recursive-descent parser | Recursive-descent supports parentheses and arbitrary nesting, but is overkill for the flat two-operator grammar needed here. Deferred to a future phase if parens are needed. |
| `re.split` token approach | `pyparsing` or `lark` | External dependencies; grammar is too simple to justify them. |

**Installation:** No new packages required.

---

## Architecture Patterns

### System Architecture Diagram

```
JSON "condition" string
        |
        v
evaluate_condition(condition, params, path)
        |
        +-- [no && or ||] --> single-atom path (existing _CONDITION_PATTERN match)
        |                         |
        |                         v
        |                    (param lookup + == / !=)
        |                         |
        |                         v
        |                      bool result
        |
        +-- [has && or ||] --> SPLIT_PATTERN.split(condition)
                                  |
                                  v
                           atoms[]: even-index tokens
                           ops[]:   odd-index tokens (&&, ||)
                                  |
                                  v
                        evaluate each atom via _ATOM_PATTERN
                        (raises WorkflowValidationError on
                         malformed atom or undefined param)
                                  |
                                  v
                        two-pass reduction:
                          pass 1: fold consecutive && into running AND
                          pass 2: OR all remaining clause values
                                  |
                                  v
                               bool result
```

### Recommended Project Structure

No structural changes. All changes stay within:

```
src/
└── data/
    └── condition_evaluator.py   # extend in-place

tests/
└── unit/
    └── test_workflow_params.py  # extend TestEvaluateCondition class
```

### Pattern 1: Token-Split Two-Pass Evaluation

**What:** Split the compound condition string on `&&`/`||` tokens using `re.split` with capturing groups (which preserves operator tokens in the result list). Atoms land at even indices; operators at odd indices. Two-pass reduction enforces `&&`-before-`||` precedence without a recursive parser.

**When to use:** Any flat expression grammar with exactly two binary infix operators where one binds tighter than the other. No parentheses needed.

**Example (verified by local prototype):**
```python
# Source: local prototype run 2026-05-31 — all 7 test cases PASS
import re

_SPLIT_PATTERN = re.compile(r'\s*(&&|\|\|)\s*')
_ATOM_PATTERN  = re.compile(
    r"^\$\{([^}]+)\}\s*(==|!=)\s*'([^']*)'\s*$"
)

def evaluate_condition(condition: str, params: dict, path: str = "") -> bool:
    tokens = _SPLIT_PATTERN.split(condition.strip())
    atoms = tokens[0::2]   # every even index: the condition atoms
    ops   = tokens[1::2]   # every odd index:  && or ||

    # Evaluate each atom (raises WorkflowValidationError on failure)
    values = [_evaluate_atom(a, params, path) for a in atoms]

    # Two-pass: && binds tighter than ||
    # Pass 1 — fold each && into the preceding clause value
    clause_values = [values[0]]
    for i, op in enumerate(ops):
        if op == '&&':
            clause_values[-1] = clause_values[-1] and values[i + 1]
        else:  # '||'
            clause_values.append(values[i + 1])

    # Pass 2 — OR all clauses
    return any(clause_values)


def _evaluate_atom(atom: str, params: dict, path: str = "") -> bool:
    """Evaluate a single atomic condition; raises WorkflowValidationError on error."""
    m = _ATOM_PATTERN.match(atom.strip())
    if not m:
        raise WorkflowValidationError(
            f"Malformed condition atom: {atom!r}. "
            "Expected format: \"${param_name} == 'value'\" or \"${param_name} != 'value'\"",
            path=path,
        )
    param_name, operator, rhs_value = m.group(1), m.group(2), m.group(3)
    if param_name not in params:
        raise WorkflowValidationError(
            f"Condition references undefined parameter '{param_name}'. "
            f"Declared parameters: {sorted(params)}",
            path=path,
        )
    lhs_value = params[param_name]
    return lhs_value == rhs_value if operator == '==' else lhs_value != rhs_value
```

**Backwards compatibility:** When `condition` is a single atom (no `&&`/`||`), `_SPLIT_PATTERN.split` returns `[atom]`, `atoms = [atom]`, `ops = []`. The two-pass reduces to `any([_evaluate_atom(atom, ...)])` — identical behaviour to the current code. [VERIFIED: prototype run]

**Operator precedence:** `&&`-before-`||` matches Python's `and`/`or` semantics and is the convention in virtually all languages. `A && B || C` evaluates as `(A and B) or C`. [VERIFIED: prototype, 7/7 test cases pass]

### Anti-Patterns to Avoid

- **Parentheses support:** Do NOT add `(`, `)` grouping in this phase. It requires a recursive-descent parser and was not requested. Flat precedence (&&-before-||) is sufficient.
- **Short-circuit evaluation:** Do NOT short-circuit (skip evaluating later atoms when result is already determined). Fail-fast error detection requires evaluating all atoms before combining, so undefined params in later atoms are caught reliably regardless of the left-hand result.
- **`eval()` or `ast.literal_eval()`:** Never use Python's `eval()` to evaluate the condition string. The grammar is tightly controlled; use the regex pattern only.
- **Mutating `_CONDITION_PATTERN`:** The old `_CONDITION_PATTERN` anchored to `^...$` matches only a single atom. Do not attempt to extend it with `&&`/`||`; replace with `_ATOM_PATTERN` + `_SPLIT_PATTERN` pair.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token splitting | Custom character-by-character parser | `re.compile(r'\s*(&&\|\|\|\|)\s*').split` | Re uses compiled NFA; handles whitespace variants cleanly with one pattern |
| Operator precedence | Explicit precedence table or Pratt parser | Two-pass fold (see Pattern 1) | Correct for exactly two operator levels with no parentheses |

---

## Common Pitfalls

### Pitfall 1: Syntax Ambiguity — ROADMAP description vs. canonical format

**What goes wrong:** The ROADMAP.md and STATE.md Phase 16 descriptions show `${account_type == 'open'}` (comparison operator INSIDE the braces). This is NOT the canonical format.

**Why it happens:** The ROADMAP entry was written informally before Phase 11 established the working grammar.

**How to avoid:** The canonical format (from Phase 11 tests and the live `_CONDITION_PATTERN` regex) puts the operator OUTSIDE the braces:
```
${param_name} == 'value'
```
The compound extension is:
```
${account_type} == 'open' && ${kyc_required} != 'true'
```

**Warning signs:** If a test uses `${account_type == 'open'}` it will fail `_ATOM_PATTERN` — this is expected, that syntax was never supported.

### Pitfall 2: Re-using the old `_CONDITION_PATTERN` for atoms

**What goes wrong:** `_CONDITION_PATTERN` is anchored with `^...$`. If you feed it a single atom extracted from a split (e.g., `"${a} == 'x'"` with trailing spaces), it still works — but if you try to match the full compound string, it will fail.

**Why it happens:** Confusion between single-atom matcher and compound string matcher.

**How to avoid:** Rename `_CONDITION_PATTERN` to `_ATOM_PATTERN` (or add `_ATOM_PATTERN` alongside) and use `_SPLIT_PATTERN` only for splitting. Never run `_CONDITION_PATTERN.match()` on a full compound string. [VERIFIED: codebase inspection]

### Pitfall 3: Empty atom from malformed split input

**What goes wrong:** Input like `"&& ${a} == 'x'"` or `"${a} == 'x' &&"` produces an empty string as one of the atoms after splitting.

**Why it happens:** The split pattern yields `['', '&&', "${a} == 'x'"]` or `["${a} == 'x'", '&&', '']`.

**How to avoid:** `_ATOM_PATTERN.match('')` returns `None`, which triggers the `WorkflowValidationError` for malformed atom. No special handling needed. [VERIFIED: prototype]

### Pitfall 4: Short-circuit skipping undefined-param errors

**What goes wrong:** If `&&` short-circuits (stops at first `False`), an undefined param in a later atom is never checked and silently passes as "false" rather than raising.

**Why it happens:** Python's `and`/`or` short-circuit by design.

**How to avoid:** Evaluate ALL atoms first (into a `values` list), then combine. This ensures undefined params in any position always raise `WorkflowValidationError`. The prototype explicitly does this.

---

## Code Examples

### Splitting a compound condition string

```python
# Source: local prototype, 2026-05-31
import re
_SPLIT_PATTERN = re.compile(r'\s*(&&|\|\|)\s*')

condition = "${account_type} == 'open' && ${kyc_required} != 'true'"
tokens = _SPLIT_PATTERN.split(condition.strip())
# Result: ["${account_type} == 'open'", '&&', "${kyc_required} != 'true'"]
atoms = tokens[0::2]  # ["${account_type} == 'open'", "${kyc_required} != 'true'"]
ops   = tokens[1::2]  # ['&&']
```

### Operator precedence reduction (two-pass)

```python
# Source: local prototype, 2026-05-31 — verified A && B || C => (A and B) or C
values = [True, False, True]  # atoms evaluated
ops    = ['&&', '||']

clause_values = [values[0]]   # [True]
# i=0, op='&&': clause_values[-1] = True and False = False  => [False]
# i=1, op='||': clause_values.append(True)                  => [False, True]
result = any(clause_values)   # True
```

### Error messages (consistent with Phase 11 patterns)

```python
# Malformed atom — raised by _evaluate_atom
raise WorkflowValidationError(
    f"Malformed condition atom: {atom!r}. "
    "Expected format: \"${param_name} == 'value'\" or \"${param_name} != 'value'\"",
    path=path,
)

# Undefined parameter — raised by _evaluate_atom
raise WorkflowValidationError(
    f"Condition references undefined parameter '{param_name}'. "
    f"Declared parameters: {sorted(params)}",
    path=path,
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_CONDITION_PATTERN` anchored single-atom match | `_SPLIT_PATTERN.split` + `_ATOM_PATTERN` per-atom | Phase 16 | Compound conditions now supported while single-atom backwards compat retained |

**Deprecated/outdated:**
- Direct use of `_CONDITION_PATTERN.match(condition.strip())` in `evaluate_condition()`: replaced by the split-then-match-each-atom approach. The underlying atom regex is reused (renamed to `_ATOM_PATTERN`).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The ROADMAP/STATE.md syntax `${param == value}` (inside braces) is informal shorthand, not a required alternate syntax | Pitfall 1, Code Examples | If the user actually wants inside-brace syntax, the entire `_ATOM_PATTERN` changes — but all existing Phase 11 tests use outside-brace format, so this is LOW risk |
| A2 | No parentheses grouping is needed for Phase 16; flat `&&`-before-`||` precedence is sufficient | Architecture Patterns | If user needs `(A \|\| B) && C`, the two-pass approach gives wrong answer — needs recursive-descent. Should clarify before planning if scope is ambiguous. |

---

## Open Questions

1. **Syntax confirmation: operators inside vs. outside braces**
   - What we know: Phase 11 tests and the live `_CONDITION_PATTERN` use `${param} == 'value'` (operators outside braces). ROADMAP/STATE.md examples show `${param == value}` (inside braces).
   - What's unclear: Was the ROADMAP example intentional, or informal?
   - Recommendation: Treat operators-outside-braces as canonical (consistent with all working Phase 11 code). If the user wants inside-brace syntax, that is a different grammar and requires a different atom pattern — raise this during planning or discuss-phase.

2. **Parentheses / grouping support**
   - What we know: The ROADMAP description does not mention parentheses. Two-pass evaluation handles `&&`-before-`||` correctly for flat expressions.
   - What's unclear: Is `(A || B) && C` a required use case?
   - Recommendation: Exclude parentheses from Phase 16 scope. Flat precedence covers all stated examples. Add a note to CONTEXT.md deferring parens to a future phase.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is purely code/logic changes within the Python stdlib. No external tools, databases, or services are required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 [VERIFIED] |
| Config file | `pytest.ini` |
| Quick run command | `pytest tests/unit/test_workflow_params.py -v` |
| Full suite command | `pytest tests/unit/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OP-01 | `A && B` both true → True | unit | `pytest tests/unit/test_workflow_params.py::TestEvaluateCondition::test_and_both_true -x` | Wave 0 |
| OP-02 | `A && B` one false → False | unit | `pytest tests/unit/test_workflow_params.py::TestEvaluateCondition::test_and_one_false -x` | Wave 0 |
| OP-03 | `A \|\| B` both false → False | unit | `pytest tests/unit/test_workflow_params.py::TestEvaluateCondition::test_or_both_false -x` | Wave 0 |
| OP-04 | `A \|\| B` one true → True | unit | `pytest tests/unit/test_workflow_params.py::TestEvaluateCondition::test_or_one_true -x` | Wave 0 |
| OP-05 | `A && B \|\| C` mixed precedence | unit | `pytest tests/unit/test_workflow_params.py::TestEvaluateCondition::test_mixed_precedence -x` | Wave 0 |
| OP-06 | Undefined param in second atom raises | unit | `pytest tests/unit/test_workflow_params.py::TestEvaluateCondition::test_undefined_param_in_compound_raises -x` | Wave 0 |
| OP-07 | Malformed second atom raises | unit | `pytest tests/unit/test_workflow_params.py::TestEvaluateCondition::test_malformed_second_atom_raises -x` | Wave 0 |
| OP-08 | Single condition still works (backwards compat) | unit | `pytest tests/unit/test_workflow_params.py::TestEvaluateCondition -x` | ✅ (existing 6 tests) |
| OP-09 | Extra whitespace around `&&`/`\|\|` tolerated | unit | `pytest tests/unit/test_workflow_params.py::TestEvaluateCondition::test_whitespace_tolerant -x` | Wave 0 |
| OP-10 | Integration: compound condition on $ref includes/omits tab | unit | `pytest tests/unit/test_workflow_params.py::TestConditionalRef -x` | Wave 0 (new test in existing class) |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/test_workflow_params.py -v`
- **Per wave merge:** `pytest tests/unit/ -v`
- **Phase gate:** Full suite green (`pytest tests/unit/ -v`) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_workflow_params.py` — extend `TestEvaluateCondition` with 8 new methods (OP-01..07, OP-09) and `TestConditionalRef` with 1 compound integration test (OP-10). File already exists; add methods only.

*(No new test files needed — all new tests extend the existing `test_workflow_params.py`.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `_ATOM_PATTERN` regex rejects malformed condition strings; `WorkflowValidationError` raised on match failure |
| V6 Cryptography | no | — |

### Known Threat Patterns for condition evaluator

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Injection via condition string | Tampering | `_ATOM_PATTERN` whitelist regex rejects any token not matching `${name} op 'value'`; no `eval()` used |
| Undefined parameter silently treated as false | Elevation of privilege | Fail-fast `WorkflowValidationError` on any undefined param reference — never silently permits |

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 16 |
|-----------|-------------------|
| Python 3.9.13 | Use `from __future__ import annotations`; no walrus operator or 3.10+ syntax |
| `from __future__ import annotations` for forward refs | Add to `condition_evaluator.py` header if not already present [VERIFIED: already present] |
| pytest for tests | All new tests in `tests/unit/test_workflow_params.py` using pytest class pattern |
| pydantic v1 or v2 — check installed version | pydantic 2.13.3 installed [VERIFIED]; use `model_validate()` pattern |
| Never use `time.sleep()` as synchronization | Not applicable — purely a data-layer logic change |
| `WorkflowValidationError` for load-time errors | All condition parse failures raise `WorkflowValidationError(message, path=path)` |
| No hardcoded env values | Not applicable — condition strings come from workflow JSON |

---

## Sources

### Primary (HIGH confidence)

- `src/data/condition_evaluator.py` — live implementation of Phase 11 evaluator [VERIFIED: file read]
- `src/data/json_loader.py` — call site for `evaluate_condition()` [VERIFIED: file read]
- `tests/unit/test_workflow_params.py` — 14 passing tests confirming Phase 11 grammar [VERIFIED: `pytest` run, 14 passed]
- `.planning/phases/11-support-workflow-parameters-conditional-ref/11-CONTEXT.md` — locked decisions (D-01 through D-07) [VERIFIED: file read]
- Local Python prototype — `re.split` two-pass evaluator, 7/7 test cases pass [VERIFIED: prototype run]

### Secondary (MEDIUM confidence)

- Python 3.9 `re` stdlib documentation — `re.compile`, `re.split` with capturing groups [ASSUMED based on stable stdlib]

### Tertiary (LOW confidence)

None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, no new deps, verified against live codebase
- Architecture: HIGH — prototype runs correctly, backwards compat confirmed
- Pitfalls: HIGH — identified from codebase inspection and prototype edge case tests

**Research date:** 2026-05-31
**Valid until:** 2026-06-30 (stable — Python stdlib and project conventions are not changing)
