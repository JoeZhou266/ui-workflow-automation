from __future__ import annotations

import re

from src.core.exceptions import WorkflowValidationError

# Matches: ${param_name} == 'value'  OR  ${param_name} != 'value'
# Groups:  (1) param_name,  (2) operator (== or !=),  (3) rhs_value
_CONDITION_PATTERN = re.compile(
    r"^\$\{([^}]+)\}\s*(==|!=)\s*'([^']*)'\s*$"
)


def evaluate_condition(condition: str, params: dict, path: str = "") -> bool:
    """Evaluate a simple ``==`` or ``!=`` condition string against *params*.

    Condition format: ``${param_name} == 'value'`` or ``${param_name} != 'value'``.
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
        WorkflowValidationError: If the condition string does not match the expected
            format (malformed condition is also an authoring error).
    """
    m = _CONDITION_PATTERN.match(condition.strip())
    if not m:
        raise WorkflowValidationError(
            f"Malformed condition string: {condition!r}. "
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
    if operator == "==":
        return lhs_value == rhs_value
    else:  # operator == "!="
        return lhs_value != rhs_value
