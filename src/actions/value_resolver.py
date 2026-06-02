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

# ---------------------------------------------------------------------------
# Env config state — populated once by configure_env_resolver() from AppConfig
# ---------------------------------------------------------------------------

_ENV_CONFIG: dict = {}


def configure_env_resolver(data: dict) -> None:
    """Populate the module-level env config dict from the loaded YAML data.

    Must be called once during ``AppConfig.__init__`` after the YAML is loaded.
    Resolution reads **only** from this dict — shell env vars and .env overrides
    do not apply (per D-03).

    Args:
        data: The raw dict returned by ``_load_yaml()``.
    """
    global _ENV_CONFIG
    _ENV_CONFIG = data


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


def resolve_dynamic_value(value: str, params: dict | None = None) -> str:
    """Resolve a ``${placeholder}`` token to a generated or parameter value.

    Resolution order:

    1. ``${env:KEY}`` — env config lookup (existing)
    2. ``PLACEHOLDER_REGISTRY`` — dynamic generator (existing)
    3. ``params`` dict — workflow parameter values (Phase 17)

    Only a *full-value* token (the entire string is the token) is expanded.
    A value like ``"prefix_${account_type}"`` is returned unchanged.

    Args:
        value: The raw string from an :class:`~src.models.workflow_models.ElementDefinition`.
        params: Optional dict mapping workflow parameter name to its resolved string value.
            When provided, checked after the registry if the key is not a registered placeholder.

    Returns:
        The resolved value if *value* is a known placeholder token,
        or *value* unchanged if it contains no placeholder.

    Raises:
        TypeError: If *value* is not a string.
        ValueError: If the token matches the placeholder pattern but is not
            registered in :data:`PLACEHOLDER_REGISTRY` and not in *params*.
    """
    if not isinstance(value, str):
        raise TypeError(
            f"resolve_dynamic_value expects a str, got {type(value).__name__!r}"
        )
    match = _PLACEHOLDER_PATTERN.match(value)
    if not match:
        return value
    key = match.group(1)
    if key.startswith("env:"):
        env_key = key[len("env:"):]
        if env_key not in _ENV_CONFIG:
            raise ValueError(
                f"Unknown env config key {env_key!r}. "
                f"Available keys: {sorted(_ENV_CONFIG)}"
            )
        return str(_ENV_CONFIG[env_key])
    if key in PLACEHOLDER_REGISTRY:
        return PLACEHOLDER_REGISTRY[key]()
    if params is not None and key in params:
        return str(params[key])
    raise ValueError(
        f"Unknown placeholder '${{{key}}}'. "
        f"Registered keys: {sorted(PLACEHOLDER_REGISTRY)}"
        + (f". Workflow params: {sorted(params)}" if params is not None else "")
    )


# ---------------------------------------------------------------------------
# ValueResolver — the Selenium action-dispatch integration point
# ---------------------------------------------------------------------------


class ValueResolver:
    """Resolves element values from the JSON definition.

    Handles ``${placeholder}`` token expansion via :func:`resolve_dynamic_value`
    and passes non-string values through unchanged.

    Args:
        params: Optional dict mapping workflow parameter name to its resolved string value.
            Injected by :class:`~src.actions.action_factory.ActionFactory` from
            :class:`~src.workflow.workflow_engine.WorkflowEngine`.
    """

    def __init__(self, params: dict | None = None) -> None:
        self._params: dict = params or {}

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
        return resolve_dynamic_value(value, params=self._params)
