"""Unit tests for placeholder resolution in value_resolver — no browser required."""
from __future__ import annotations

from unittest.mock import patch
import pytest

from src.actions.value_resolver import (
    PLACEHOLDER_REGISTRY,
    ValueResolver,
    generate_first_name,
    generate_last_name,
    generate_sin_number,
    resolve_dynamic_value,
)


# ---------------------------------------------------------------------------
# Luhn validation helper (used by TestGenerators only)
# ---------------------------------------------------------------------------

def _luhn_valid(sin: str) -> bool:
    """Return True if *sin* passes the Luhn mod-10 check used by Canadian SINs."""
    digits = [int(c) for c in sin]
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            doubled = d * 2
            total += doubled if doubled < 10 else doubled - 9
        else:
            total += d
    return total % 10 == 0


# ---------------------------------------------------------------------------
# SC-4, SC-5: Generator functions
# ---------------------------------------------------------------------------

class TestGenerators:
    def test_sin_length(self):
        assert len(generate_sin_number()) == 9

    def test_sin_all_digits(self):
        assert generate_sin_number().isdigit()

    def test_sin_first_digit(self):
        for _ in range(50):
            assert generate_sin_number()[0] in "12345678"

    def test_sin_luhn_valid(self):
        for _ in range(20):
            assert _luhn_valid(generate_sin_number())

    def test_sin_randomness(self):
        results = {generate_sin_number() for _ in range(20)}
        assert len(results) > 1

    def test_first_name_nonempty(self):
        assert isinstance(generate_first_name(), str)
        assert len(generate_first_name()) > 0

    def test_last_name_nonempty(self):
        assert isinstance(generate_last_name(), str)
        assert len(generate_last_name()) > 0


# ---------------------------------------------------------------------------
# SC-1, SC-2: PLACEHOLDER_REGISTRY and resolve_dynamic_value()
# ---------------------------------------------------------------------------

class TestPlaceholderRegistry:
    def test_registry_keys_exist(self):
        assert "sin_number" in PLACEHOLDER_REGISTRY
        assert "first_name" in PLACEHOLDER_REGISTRY
        assert "last_name" in PLACEHOLDER_REGISTRY

    def test_registry_values_are_callable(self):
        for key, fn in PLACEHOLDER_REGISTRY.items():
            assert callable(fn), f"Registry entry '{key}' is not callable"

    def test_resolve_sin_number(self):
        result = resolve_dynamic_value("${sin_number}")
        assert isinstance(result, str)
        assert len(result) == 9
        assert result.isdigit()

    def test_resolve_first_name(self):
        result = resolve_dynamic_value("${first_name}")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_resolve_last_name(self):
        result = resolve_dynamic_value("${last_name}")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_passthrough_no_placeholder(self):
        assert resolve_dynamic_value("plain text") == "plain text"

    def test_passthrough_empty_string(self):
        assert resolve_dynamic_value("") == ""

    def test_passthrough_mixed_string(self):
        # Partial token must NOT expand — only full-value tokens are resolved
        original = "prefix_${sin_number}"
        assert resolve_dynamic_value(original) == original

    def test_passthrough_mixed_string_suffix(self):
        original = "${sin_number}_suffix"
        assert resolve_dynamic_value(original) == original

    def test_unknown_placeholder_raises(self):
        with pytest.raises(ValueError, match="Unknown placeholder"):
            resolve_dynamic_value("${nonexistent_key}")

    def test_non_string_input_raises_type_error(self):
        with pytest.raises(TypeError):
            resolve_dynamic_value(None)  # type: ignore[arg-type]

    def test_non_string_int_raises_type_error(self):
        with pytest.raises(TypeError):
            resolve_dynamic_value(42)  # type: ignore[arg-type]

    def test_custom_generator_via_patch(self):
        with patch.dict(PLACEHOLDER_REGISTRY, {"custom_key": lambda: "fixed_value"}):
            assert resolve_dynamic_value("${custom_key}") == "fixed_value"
        # Registry restored — custom_key must no longer be present
        assert "custom_key" not in PLACEHOLDER_REGISTRY


# ---------------------------------------------------------------------------
# SC-3: ValueResolver.resolve() wires through to resolve_dynamic_value()
# ---------------------------------------------------------------------------

class TestValueResolverIntegration:
    def test_resolver_expands_sin(self):
        r = ValueResolver()
        result = r.resolve("${sin_number}")
        assert isinstance(result, str)
        assert len(result) == 9
        assert result.isdigit()

    def test_resolver_expands_first_name(self):
        r = ValueResolver()
        result = r.resolve("${first_name}")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_resolver_passthrough_plain_string(self):
        r = ValueResolver()
        assert r.resolve("hello") == "hello"

    def test_resolver_passthrough_none(self):
        r = ValueResolver()
        assert r.resolve(None) is None

    def test_resolver_passthrough_int(self):
        r = ValueResolver()
        assert r.resolve(42) == 42

    def test_resolver_unknown_placeholder_raises(self):
        r = ValueResolver()
        with pytest.raises(ValueError, match="Unknown placeholder"):
            r.resolve("${bad_token}")
