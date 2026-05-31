---
phase: 16-support-logical-operators-conditional-ref
reviewed: 2026-05-31T23:04:43Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/data/condition_evaluator.py
  - tests/unit/test_workflow_params.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-05-31T23:04:43Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed `condition_evaluator.py` (the new compound-condition evaluator introduced in Phase 16) and `test_workflow_params.py` (its unit + integration test suite). The core logic for `&&`/`||` operator support with correct precedence (`&&` tighter than `||`) is implemented correctly and the two-pass reduction algorithm produces the right results. The test suite covers all documented scenarios (OP-01 through OP-07, OP-09, OP-10) with a missing OP-08 entry noted below.

One warning-level correctness bug was found: the `_SPLIT_PATTERN` regex splits on `&&` or `||` anywhere in the condition string, including inside single-quoted RHS values. A condition atom such as `${a} == '&&'` is split incorrectly, producing a misleading "Malformed" error rather than evaluating the atom. Two info items cover a missing test case and a design limitation on value characters.

## Warnings

### WR-01: `_SPLIT_PATTERN` incorrectly splits on `&&`/`||` inside quoted RHS values

**File:** `src/data/condition_evaluator.py:15`

**Issue:** `_SPLIT_PATTERN = re.compile(r'\s*(&&|\|\|)\s*')` is applied to the raw condition string before any quoting context is considered. If a workflow author writes a condition such as `${a} == '&&'` or `${b} != '||'`, the regex splits on the operator literal inside the quoted value, producing tokens like `["${a} == '", "&&", "'"]`. The subsequent call to `_evaluate_atom` then fails with "Malformed condition atom" — a misleading error that gives no hint that the value itself was the problem.

Confirmed via Python:
```
>>> re.compile(r'\s*(&&|\|\|)\s*').split("${a} == '&&'")
["${a} == '", '&&', "'"]
```

**Fix:** Apply the split only outside quoted regions. A straightforward approach is to replace the `re.split` pass with a small hand-rolled tokenizer that respects single-quote context:

```python
def _split_tokens(condition: str) -> list[str]:
    """Split condition on && / || operators outside single-quoted strings."""
    tokens: list[str] = []
    current: list[str] = []
    i = 0
    in_quote = False
    while i < len(condition):
        if condition[i] == "'" and not in_quote:
            in_quote = True
            current.append(condition[i])
            i += 1
        elif condition[i] == "'" and in_quote:
            in_quote = False
            current.append(condition[i])
            i += 1
        elif not in_quote and condition[i:i+2] in ("&&", "||"):
            tokens.append("".join(current).strip())
            tokens.append(condition[i:i+2])
            current = []
            i += 2
        else:
            current.append(condition[i])
            i += 1
    tokens.append("".join(current).strip())
    return tokens
```

Then replace line 40:
```python
# Before
tokens = _SPLIT_PATTERN.split(condition.strip())

# After
tokens = _split_tokens(condition.strip())
```

Note: values containing single quotes (e.g., `O'Brien`) remain unsupported by `_ATOM_PATTERN` regardless — that is a separate, pre-existing limitation (see IN-02).

## Info

### IN-01: Missing OP-08 test case in `TestEvaluateCondition`

**File:** `tests/unit/test_workflow_params.py:119`

**Issue:** The test IDs in `TestEvaluateCondition` jump from `# OP-07` (line 115) to `# OP-09` (line 119) with no `# OP-08` entry. The design spec (Phase 16 plan) presumably defined an OP-08 scenario that was never implemented. If OP-08 was intentionally dropped, the comment gap is confusing; if it was forgotten, coverage is incomplete.

**Fix:** Either add the missing OP-08 test, or add a brief comment explaining why it was skipped:
```python
# OP-08: (intentionally omitted — scenario superseded by OP-09)
```

### IN-02: `_ATOM_PATTERN` silently rejects single quotes in RHS values

**File:** `src/data/condition_evaluator.py:9`

**Issue:** The atom regex `'([^']*)'` allows only values that contain no single-quote characters. A condition such as `${name} == 'O'Brien'` fails with "Malformed condition atom" rather than a more informative error explaining that single quotes in values are unsupported. The error message mentions the expected format but does not call out this specific constraint.

**Fix:** Add the constraint to the error message raised in `_evaluate_atom` (line 77-81):
```python
raise WorkflowValidationError(
    f"Malformed condition atom: {atom!r}. "
    "Expected format: \"${param_name} == 'value'\" or \"${param_name} != 'value'\". "
    "Values must not contain single-quote characters.",
    path=path,
)
```

Alternatively, if single quotes in values are a realistic need, switch to double-quoted values with a double-quote escape sequence (`\"`), or support both quote styles in the regex.

---

_Reviewed: 2026-05-31T23:04:43Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
