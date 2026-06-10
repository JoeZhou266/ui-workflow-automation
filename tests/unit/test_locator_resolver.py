"""Unit tests for LocatorResolver — no browser required."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from selenium.webdriver.common.by import By

from src.core.exceptions import LocatorResolutionError
from src.locators.locator_resolver import LocatorResolver
from src.models.workflow_models import ElementDefinition, LocatorDefinition
from src.core.enums import ActionType, ElementType


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


# ---------------------------------------------------------------------------
# Phase 21 — LP-06..LP-09: ActionFactory integration with locator param resolution
# ---------------------------------------------------------------------------


class TestLocatorResolverWithParams:
    """LP-06..LP-09: ActionFactory._resolve_locator integration — seam is option (b).

    Tests the FULL wiring through ActionFactory._resolve_locator (upstream seam).
    Per the seam decision in 21-01-PLAN.md, option (b) is used: resolve in ActionFactory,
    NOT via a params kwarg on LocatorResolver.resolve (that signature does not exist here).
    """

    def _make_element(self, locator_value: str, by: str = "id") -> ElementDefinition:
        """Build a minimal ElementDefinition with the given locator value."""
        return ElementDefinition(
            name="test_element",
            type=ElementType.BUTTON,
            action=ActionType.CLICK,
            locator=LocatorDefinition(by=by, value=locator_value),
        )

    # LP-06: _resolve_locator returns resolved LocatorDefinition with expanded value
    def test_resolve_locator_expands_full_token(self):
        """LP-06: ActionFactory._resolve_locator expands full-value ${company_code} from params."""
        from src.actions.action_factory import ActionFactory

        mock_page = MagicMock()
        mock_wm = MagicMock()
        factory = ActionFactory(mock_page, mock_wm, params={"company_code": "ACME"})

        locator = LocatorDefinition(by="id", value="${company_code}")
        resolved = factory._resolve_locator(locator)
        assert resolved.value == "ACME"
        assert resolved.by == "id"

    # LP-07: _resolve_locator with no params returns the SAME object (identity)
    def test_resolve_locator_no_params_returns_identity(self):
        """LP-07: With empty params dict, _resolve_locator returns the same locator object."""
        from src.actions.action_factory import ActionFactory

        mock_page = MagicMock()
        mock_wm = MagicMock()
        factory = ActionFactory(mock_page, mock_wm, params={})

        locator = LocatorDefinition(by="id", value="static_id")
        result = factory._resolve_locator(locator)
        # No params → must return the same object (zero allocation)
        assert result is locator

    # LP-07 (no tokens): selector without tokens, params present → same object
    def test_resolve_locator_no_token_returns_identity(self):
        """LP-07: Selector without ${...} tokens returns the same locator object even with params."""
        from src.actions.action_factory import ActionFactory

        mock_page = MagicMock()
        mock_wm = MagicMock()
        factory = ActionFactory(mock_page, mock_wm, params={"company_code": "ACME"})

        locator = LocatorDefinition(by="id", value="static_id")
        result = factory._resolve_locator(locator)
        assert result is locator

    # LP-08: unknown token raises ValueError
    def test_resolve_locator_unknown_token_raises(self):
        """LP-08: Unknown ${token} in locator raises ValueError matching 'Unknown locator param'."""
        from src.actions.action_factory import ActionFactory

        mock_page = MagicMock()
        mock_wm = MagicMock()
        factory = ActionFactory(mock_page, mock_wm, params={})

        locator = LocatorDefinition(by="id", value="${missing_param}")
        with pytest.raises(ValueError, match="Unknown locator param"):
            factory._resolve_locator(locator)

    # LP-09: run()-level test — element passed to execute carries resolved locator value
    def test_run_passes_resolved_element_to_execute(self):
        """LP-09: factory.run() ensures the element passed to execute has the resolved locator value."""
        from src.actions.action_factory import ActionFactory

        mock_page = MagicMock()
        mock_page.is_visible.return_value = True
        mock_wm = MagicMock()
        factory = ActionFactory(mock_page, mock_wm, params={"company_code": "ACME"})

        element = self._make_element("${company_code}", by="id")

        executed_elements = []

        def capture_execute(elem, val):
            executed_elements.append(elem)

        with patch.object(factory._executor, "execute", side_effect=capture_execute):
            factory.run(element)

        assert len(executed_elements) == 1
        assert executed_elements[0].locator.value == "ACME"
