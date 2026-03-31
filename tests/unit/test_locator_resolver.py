"""Unit tests for LocatorResolver — no browser required."""
from __future__ import annotations

import pytest
from selenium.webdriver.common.by import By

from src.core.exceptions import LocatorResolutionError
from src.locators.locator_resolver import LocatorResolver
from src.models.workflow_models import LocatorDefinition


class TestLocatorResolver:
    @pytest.mark.parametrize("by,expected", [
        ("id", By.ID),
        ("name", By.NAME),
        ("class_name", By.CLASS_NAME),
        ("css_selector", By.CSS_SELECTOR),
        ("xpath", By.XPATH),
        ("link_text", By.LINK_TEXT),
        ("partial_link_text", By.PARTIAL_LINK_TEXT),
        ("tag_name", By.TAG_NAME),
    ])
    def test_resolve_all_strategies(self, by, expected):
        locator = LocatorDefinition(by=by, value="selector")
        result_by, result_value = LocatorResolver.resolve(locator)
        assert result_by == expected
        assert result_value == "selector"

    def test_resolve_preserves_selector_value(self):
        locator = LocatorDefinition(by="css_selector", value=".my-class > input[type='text']")
        _, value = LocatorResolver.resolve(locator)
        assert value == ".my-class > input[type='text']"

    def test_resolve_returns_tuple(self):
        locator = LocatorDefinition(by="id", value="myId")
        result = LocatorResolver.resolve(locator)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_resolve_with_element_name_context(self):
        locator = LocatorDefinition(by="id", value="x")
        by, _ = LocatorResolver.resolve(locator, element_name="Username Field")
        assert by == By.ID

    def test_supported_strategies_returns_list(self):
        strategies = LocatorResolver.supported_strategies()
        assert isinstance(strategies, list)
        assert "id" in strategies
        assert "css_selector" in strategies
        assert "xpath" in strategies

    def test_invalid_locator_raises_at_model_validation(self):
        """LocatorDefinition itself rejects unknown strategies."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LocatorDefinition(by="data-testid", value="x")

    def test_id_locator_resolves_correctly(self):
        loc = LocatorDefinition(by="id", value="username")
        by, val = LocatorResolver.resolve(loc)
        assert by == By.ID
        assert val == "username"

    def test_xpath_locator(self):
        locator = LocatorDefinition(by="xpath", value="//div[@class='foo']//input")
        by, val = LocatorResolver.resolve(locator)
        assert by == By.XPATH
        assert val == "//div[@class='foo']//input"
