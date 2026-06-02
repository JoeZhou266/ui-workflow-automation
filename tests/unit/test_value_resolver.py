"""Unit tests for placeholder resolution in value_resolver — no browser required."""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime
from unittest.mock import patch
import pytest

from src.actions.value_resolver import (
    PLACEHOLDER_REGISTRY,
    ValueResolver,
    configure_env_resolver,
    generate_first_name,
    generate_last_day_of_next_month,
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
    def _full_sin(self) -> str:
        """Assemble a full 9-digit SIN from 3 consecutive chunk calls."""
        return generate_sin_number() + generate_sin_number() + generate_sin_number()

    def test_sin_length(self):
        # generate_sin_number() returns 3-digit chunks; 3 calls = full 9-digit SIN
        assert len(self._full_sin()) == 9

    def test_sin_all_digits(self):
        assert self._full_sin().isdigit()

    def test_sin_first_digit(self):
        for _ in range(50):
            full = self._full_sin()
            assert full[0] in "12345678"

    def test_sin_luhn_valid(self):
        for _ in range(20):
            assert _luhn_valid(self._full_sin())

    def test_sin_randomness(self):
        results = {self._full_sin() for _ in range(20)}
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
        # generate_sin_number() returns 3-digit chunks; 3 calls assemble a full SIN
        chunk1 = resolve_dynamic_value("${sin_number}")
        chunk2 = resolve_dynamic_value("${sin_number}")
        chunk3 = resolve_dynamic_value("${sin_number}")
        result = chunk1 + chunk2 + chunk3
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
        # generate_sin_number() returns 3-digit chunks; 3 calls assemble a full SIN
        r = ValueResolver()
        chunk1 = r.resolve("${sin_number}")
        chunk2 = r.resolve("${sin_number}")
        chunk3 = r.resolve("${sin_number}")
        result = chunk1 + chunk2 + chunk3
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


# ---------------------------------------------------------------------------
# Phase 9 — SC-1..SC-5: generate_last_day_of_next_month and registry integration
# ---------------------------------------------------------------------------

class TestLastDayOfNextMonth:
    def test_format_is_mm_dd_yyyy(self):
        result = generate_last_day_of_next_month()
        assert re.fullmatch(r"\d{2}/\d{2}/\d{4}", result), f"Bad format: {result}"

    def test_last_day_correct_for_next_month(self):
        result = generate_last_day_of_next_month()
        parsed = datetime.strptime(result, "%m/%d/%Y").date()
        today = date.today()
        if today.month == 12:
            exp_year, exp_month = today.year + 1, 1
        else:
            exp_year, exp_month = today.year, today.month + 1
        assert parsed.month == exp_month
        assert parsed.year == exp_year
        assert parsed.day == calendar.monthrange(exp_year, exp_month)[1]

    def test_leap_year_february_next_month(self):
        # today = Jan 2024 → next month = Feb 2024 (leap year)
        with patch("src.actions.value_resolver.date") as mock_date:
            mock_date.today.return_value = date(2024, 1, 1)
            assert generate_last_day_of_next_month() == "02/29/2024"

    def test_non_leap_year_february_next_month(self):
        # today = Jan 2023 → next month = Feb 2023 (non-leap)
        with patch("src.actions.value_resolver.date") as mock_date:
            mock_date.today.return_value = date(2023, 1, 1)
            assert generate_last_day_of_next_month() == "02/28/2023"

    def test_month_with_30_days(self):
        # today = Mar 2026 → next month = Apr 2026 (30 days)
        with patch("src.actions.value_resolver.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 1)
            assert generate_last_day_of_next_month() == "04/30/2026"

    def test_month_with_31_days(self):
        # today = Nov 2026 → next month = Dec 2026 (31 days)
        with patch("src.actions.value_resolver.date") as mock_date:
            mock_date.today.return_value = date(2026, 11, 1)
            assert generate_last_day_of_next_month() == "12/31/2026"

    def test_december_wraps_to_january_next_year(self):
        # today = Dec 2026 → next month = Jan 2027 (31 days, year rolls over)
        with patch("src.actions.value_resolver.date") as mock_date:
            mock_date.today.return_value = date(2026, 12, 1)
            assert generate_last_day_of_next_month() == "01/31/2027"

    def test_registry_key_exists(self):
        assert "last_day_of_next_month" in PLACEHOLDER_REGISTRY
        assert callable(PLACEHOLDER_REGISTRY["last_day_of_next_month"])

    def test_resolve_last_day_via_registry(self):
        result = resolve_dynamic_value("${last_day_of_next_month}")
        assert isinstance(result, str)
        assert re.fullmatch(r"\d{2}/\d{2}/\d{4}", result) is not None

    def test_passthrough_non_placeholder_unchanged(self):
        assert resolve_dynamic_value("05/31/2026") == "05/31/2026"


# ---------------------------------------------------------------------------
# Phase 10 — SC-1..SC-4: ${env:KEY} placeholder resolution
# ---------------------------------------------------------------------------

class TestEnvPlaceholder:
    def test_resolves_known_key(self):
        configure_env_resolver({"base_url": "http://test.example.com"})
        assert resolve_dynamic_value("${env:base_url}") == "http://test.example.com"

    def test_resolves_custom_key(self):
        configure_env_resolver({"account_number": "ACC-001"})
        assert resolve_dynamic_value("${env:account_number}") == "ACC-001"

    def test_missing_key_raises_value_error(self):
        configure_env_resolver({"base_url": "http://test.example.com"})
        with pytest.raises(ValueError, match="Unknown env config key 'MISSING_KEY'"):
            resolve_dynamic_value("${env:MISSING_KEY}")

    def test_missing_key_error_lists_available_keys(self):
        configure_env_resolver({"base_url": "http://test.example.com", "account_number": "ACC-001"})
        with pytest.raises(ValueError) as exc_info:
            resolve_dynamic_value("${env:nonexistent}")
        assert "Available keys:" in str(exc_info.value)

    def test_empty_env_config_raises_on_any_key(self):
        configure_env_resolver({})
        with pytest.raises(ValueError, match="Unknown env config key"):
            resolve_dynamic_value("${env:anything}")

    def test_env_and_registry_placeholders_coexist(self):
        configure_env_resolver({"login_password": "secret99"})
        env_result = resolve_dynamic_value("${env:login_password}")
        # generate_sin_number() returns 3-digit chunks; 3 calls assemble a full SIN
        sin_chunk1 = resolve_dynamic_value("${sin_number}")
        sin_chunk2 = resolve_dynamic_value("${sin_number}")
        sin_chunk3 = resolve_dynamic_value("${sin_number}")
        sin_result = sin_chunk1 + sin_chunk2 + sin_chunk3
        assert env_result == "secret99"
        assert isinstance(sin_result, str) and len(sin_result) == 9

    def test_passthrough_non_placeholder_unchanged(self):
        configure_env_resolver({"base_url": "http://test.example.com"})
        assert resolve_dynamic_value("plain text") == "plain text"

    def test_configure_env_resolver_callable(self):
        assert callable(configure_env_resolver)


# ---------------------------------------------------------------------------
# Phase 17 — VP-01..VP-10: Parameter value expansion in element values
# ---------------------------------------------------------------------------


class TestParamExpansion:
    """VP-01..VP-10: Workflow parameter names resolve as ${param_name} in element values."""

    # VP-01
    def test_param_resolved_by_name(self):
        result = resolve_dynamic_value("${account_type}", params={"account_type": "OPEN"})
        assert result == "OPEN"

    # VP-02
    def test_unknown_param_raises_with_params_listed(self):
        with pytest.raises(ValueError) as exc_info:
            resolve_dynamic_value("${account_type}", params={})
        msg = str(exc_info.value)
        assert "Unknown placeholder" in msg
        assert "Workflow params:" in msg

    # VP-03
    def test_registry_priority_over_params(self):
        # "sin_number" is in PLACEHOLDER_REGISTRY; a param with the same name must NOT shadow it
        result = resolve_dynamic_value("${sin_number}", params={"sin_number": "fixed"})
        # Registry generator returns a 3-digit chunk, not the static "fixed" value
        assert result != "fixed"
        assert len(result) == 3 and result.isdigit()

    # VP-04
    def test_no_params_unknown_key_raises(self):
        with pytest.raises(ValueError, match="Unknown placeholder"):
            resolve_dynamic_value("${param_name}", params=None)

    # VP-05
    def test_value_resolver_with_params(self):
        r = ValueResolver(params={"acct": "123"})
        assert r.resolve("${acct}") == "123"

    # VP-06
    def test_value_resolver_unknown_raises(self):
        r = ValueResolver(params={})
        with pytest.raises(ValueError, match="Unknown placeholder"):
            r.resolve("${unknown_key}")

    # VP-07
    def test_non_string_passthrough(self):
        r = ValueResolver(params={"x": "val"})
        assert r.resolve(42) == 42

    # VP-08
    def test_none_passthrough(self):
        r = ValueResolver(params={"x": "val"})
        assert r.resolve(None) is None

    # VP-09
    def test_partial_token_not_expanded(self):
        # Full-value-only semantics: "prefix_${name}" must NOT expand
        r = ValueResolver(params={"name": "Alice"})
        assert r.resolve("prefix_${name}") == "prefix_${name}"

    # VP-10
    def test_action_factory_integration(self):
        """ActionFactory with params resolves ${param} element value via injected resolver."""
        from unittest.mock import MagicMock, patch
        from src.actions.action_factory import ActionFactory

        mock_page = MagicMock()
        mock_wm = MagicMock()
        factory = ActionFactory(mock_page, mock_wm, params={"acct": "OPEN"})

        element = MagicMock()
        element.value = "${acct}"
        element.pre_wait = None
        element.post_wait = None
        element.retryable = False
        element.retry_count = 0
        element.options = {}
        element.name = "test_element"
        element.action.value = "input"
        element.type.value = "text"

        resolved_values = []

        def capture_execute(elem, resolved_val):
            resolved_values.append(resolved_val)

        with patch.object(factory._executor, "execute", side_effect=capture_execute):
            factory.run(element)

        assert resolved_values == ["OPEN"]
