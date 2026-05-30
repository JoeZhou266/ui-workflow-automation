from __future__ import annotations

import calendar
import random
import re
import secrets
from datetime import date, datetime
from typing import Any, Callable, Dict, Optional

# ---------------------------------------------------------------------------
# Placeholder pattern — anchored so only a full-value token matches.
# A value like "prefix_${sin_number}" is NOT a match and is returned as-is.
# ---------------------------------------------------------------------------

_PLACEHOLDER_PATTERN = re.compile(r"^\$\{([^}]+)\}$")

# ---------------------------------------------------------------------------
# Generator functions (defined before PLACEHOLDER_REGISTRY so they are in scope)
# ---------------------------------------------------------------------------

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

def generate_random_number(length = 7) -> str:
    """Return a random number with a specified number of digits."""
    return ''.join(str(secrets.randbelow(10)) for _ in range(length))

# ------------------------------------------------------------------------------
# SIN number state management – for chunked three-field SIN input
# ------------------------------------------------------------------------------

_sin_state: Dict[str, Any] = {
    "current_sin": None,
    "call_count": 0,
}

def _generate_sin_full() -> str:  # 1 usage  new*
    """Generate and store a complete 9-digit SIN, reset state."""
    first = random.randint(a=1, b=8)
    rest = [random.randint(a=0, b=9) for _ in range(7)]
    digits_8 = [first] + rest
    total = 0
    for i, d in enumerate(digits_8):
        if i % 2 == 1:  # odd-indexed from left: double
            doubled = d * 2
            total += doubled if doubled < 10 else doubled - 9
        else:
            total += d
    check = (10 - (total % 10)) % 10
    full_sin = "".join(str(d) for d in digits_8 + [check])
    _sin_state["current_sin"] = full_sin
    _sin_state["call_count"] = 0
    return full_sin

def generate_sin_number() -> str:  # 1 usage  new*
    """Return successive 3-digit chunks of a 9-digit SIN across three calls.

    On the first call, generates a complete valid 9-digit SIN and returns digits 0-2.
    On the second call, returns digits 3-5 of the same SIN.
    On the third call, returns digits 6-8 of the same SIN.
    After the third call, the next call will generate a new SIN and restart the cycle.

    Each generated SIN passes the Canadian SIN Luhn mod-10 check.
    First digit is 1-8 (digits 0 and 9 are reserved). Check digit is computed
    using the Luhn algorithm: double digits at odd indices (0-indexed from the
    left of the 8-prefix), subtract 9 if the doubled value exceeds 9, sum all
    values, then append ``(10 - total % 10) % 10``.
    """
    if _sin_state["current_sin"] is None or _sin_state["call_count"] >= 3:
        _generate_sin_full()

    sin = _sin_state["current_sin"]
    chunk_index = _sin_state["call_count"]
    start_idx = chunk_index * 3
    chunk = sin[start_idx : start_idx + 3]
    _sin_state["call_count"] += 1

    return chunk


def generate_first_name() -> str:
    """Return a random first name from the built-in name list."""
    return random.choice(_FIRST_NAMES)


def generate_last_name() -> str:
    """Return a random last name from the built-in name list."""
    return random.choice(_LAST_NAMES)


def generate_last_day_of_next_month() -> str:
    """Return the last calendar day of next month as MM/DD/YYYY.

    Uses ``calendar.monthrange()`` to determine the last day, which handles
    all months correctly including leap-year February and December → January
    year-wrap.

    Returns:
        A date string formatted as MM/DD/YYYY (e.g. ``"06/30/2026"`` when
        called in May 2026).
    """
    today = date.today()
    if today.month == 12:
        next_year, next_month = today.year + 1, 1
    else:
        next_year, next_month = today.year, today.month + 1
    last_day = calendar.monthrange(next_year, next_month)[1]
    return datetime(next_year, next_month, last_day).strftime("%m/%d/%Y")


# ---------------------------------------------------------------------------
# Registry — maps placeholder token names to zero-argument generator callables.
# Each call produces a fresh value; generators are not cached.
# To add a new placeholder: add an entry here and define the generator above.
# ---------------------------------------------------------------------------

PLACEHOLDER_REGISTRY: Dict[str, Callable[[], str]] = {
    "sin_number": generate_sin_number,
    "first_name": generate_first_name,
    "last_name": generate_last_name,
    "last_day_of_next_month": generate_last_day_of_next_month,
    "random_number": generate_random_number,
}


def resolve_dynamic_value(value: str) -> str:
    """Resolve a ``${placeholder}`` token to a generated value.

    Only a *full-value* token (the entire string is the token) is expanded.
    A value like ``"prefix_${sin_number}"`` is returned unchanged.

    Args:
        value: The raw string from an :class:`~src.models.workflow_models.ElementDefinition`.

    Returns:
        The generated value if *value* is a registered placeholder token,
        or *value* unchanged if it contains no placeholder.

    Raises:
        ValueError: If the token matches the placeholder pattern but is not
            registered in :data:`PLACEHOLDER_REGISTRY`.
    """
    if not isinstance(value, str):
        raise TypeError(
            f"resolve_dynamic_value expects a str, got {type(value).__name__!r}"
        )
    match = _PLACEHOLDER_PATTERN.match(value)
    if not match:
        return value
    key = match.group(1)
    if key not in PLACEHOLDER_REGISTRY:
        raise ValueError(
            f"Unknown placeholder '${{{key}}}'. "
            f"Registered keys: {sorted(PLACEHOLDER_REGISTRY)}"
        )
    return PLACEHOLDER_REGISTRY[key]()


# ---------------------------------------------------------------------------
# ValueResolver — the Selenium action-dispatch integration point
# ---------------------------------------------------------------------------


class ValueResolver:
    """Resolves element values from the JSON definition.

    Handles ``${placeholder}`` token expansion via :func:`resolve_dynamic_value`
    and passes non-string values through unchanged.
    """

    def resolve(self, value: Optional[Any]) -> Optional[Any]:
        """Return the resolved value.

        Args:
            value: Raw value from :class:`~src.models.workflow_models.ElementDefinition`.

        Returns:
            The resolved value, ready to pass to a Selenium action.
        """
        if value is None:
            return None
        if isinstance(value, str):
            return self._resolve_string(value)
        return value

    def _resolve_string(self, value: str) -> str:
        return resolve_dynamic_value(value)
