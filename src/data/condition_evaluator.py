from __future__ import annotations

import re

from src.core.exceptions import WorkflowValidationError

# Matches a single atomic condition: ${param_name} == 'value'  OR  ${param_name} != 'value'
# Groups:  (1) param_name,  (2) operator (== or !=),  (3) rhs_value
_ATOM_PATTERN = re.compile(
    r"^\$\{([^}]+)\}\s*(==|!=)\s*'([^']*)'\s*$"
)

# Splits compound conditions on && or || operators (whitespace-tolerant).
# Using a capturing group preserves operator tokens at odd indices of the result list.
_SPLIT_PATTERN = re.compile(r'\s*(&&|\|\|)\s*')


def evaluate_condition(condition: str, params: dict, path: str = "") -> bool:
    """Evaluate a simple ``==`` or ``!=`` condition string against *params*.

    Condition format: ``${param_name} == 'value'`` or ``${param_name} != 'value'``.
    Compound conditions using ``&&`` and ``||`` are also supported (Phase 16).
    Operator precedence: ``&&`` binds tighter than ``||``.
    String comparison only — no type coercion (per D-06).

    Args:
        condition: The raw condition string from the $ref node's "condition" key.
        params: Dict mapping parameter names to resolved string values.
        path: Workflow file path for error context (passed to WorkflowValidationError).

    Returns:
        True if the condition evaluates to true; False otherwise.

    Raises:
        WorkflowValidationError: If the condition references an undefined parameter name
            (per D-03 — fail fast).
        WorkflowValidationError: If any atom in the condition string does not match the
            expected format (malformed condition is also an authoring error).
    """
    tokens = _SPLIT_PATTERN.split(condition.strip())
    atoms = tokens[0::2]   # even-index tokens: the condition atoms
    ops   = tokens[1::2]   # odd-index tokens:  && or ||

    # Evaluate ALL atoms first — fail-fast: catches undefined params anywhere in the expression.
    # Do NOT short-circuit: an undefined param in a later atom must always raise.
    values = [_evaluate_atom(a, params, path) for a in atoms]

    # Two-pass reduction: && binds tighter than ||
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
    """Evaluate a single atomic condition; raises WorkflowValidationError on error.

    Args:
        atom: A single stripped atom string, e.g. "${param_name} == 'value'".
        params: Dict mapping parameter names to resolved string values.
        path: Workflow file path for error context.

    Returns:
        True if the atom evaluates to true; False otherwise.

    Raises:
        WorkflowValidationError: If atom does not match _ATOM_PATTERN or param is undefined.
    """
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
    return lhs_value == rhs_value if operator == "==" else lhs_value != rhs_value
