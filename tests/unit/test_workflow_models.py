"""Unit tests for Pydantic workflow models — no browser required."""
from __future__ import annotations

import pydantic
import pytest
from pydantic import ValidationError

_PYDANTIC_V2 = int(pydantic.VERSION.split(".")[0]) >= 2
requires_pydantic_v2 = pytest.mark.skipif(
    not _PYDANTIC_V2, reason="Pydantic v2 required for model_validate"
)

from src.models.workflow_models import (
    ElementDefinition,
    LocatorDefinition,
    LoadCriteria,
    PageDefinition,
    SectionDefinition,
    TabDefinition,
    WaitConditionDefinition,
    WorkflowDefinition,
)
from src.core.enums import ActionType, ElementType, WaitConditionType


# ---------------------------------------------------------------------------
# LocatorDefinition
# ---------------------------------------------------------------------------

class TestLocatorDefinition:
    def test_valid_locator(self):
        loc = LocatorDefinition(by="id", value="myId")
        assert loc.by == "id"
        assert loc.value == "myId"

    @pytest.mark.parametrize("by", [
        "id", "name", "class_name", "css_selector",
        "xpath", "link_text", "partial_link_text", "tag_name",
    ])
    def test_all_supported_strategies(self, by):
        loc = LocatorDefinition(by=by, value="x")
        assert loc.by == by

    def test_invalid_by_raises(self):
        with pytest.raises(ValidationError, match="Unknown locator strategy"):
            LocatorDefinition(by="unknown_strategy", value="x")

    def test_empty_value_is_allowed(self):
        # Empty selector string is structurally valid (runtime may fail, not model)
        loc = LocatorDefinition(by="id", value="")
        assert loc.value == ""


# ---------------------------------------------------------------------------
# ElementDefinition
# ---------------------------------------------------------------------------

class TestElementDefinition:
    def _make_locator(self):
        return LocatorDefinition(by="id", value="el")

    def test_minimal_element(self):
        el = ElementDefinition(
            name="Submit",
            type=ElementType.BUTTON,
            action=ActionType.CLICK,
            locator=self._make_locator(),
        )
        assert el.name == "Submit"
        assert el.required is False
        assert el.retryable is False
        assert el.retry_count == 0

    def test_required_input_without_value_raises(self):
        with pytest.raises(ValidationError):
            ElementDefinition(
                name="Email",
                type=ElementType.TEXT,
                action=ActionType.INPUT,
                locator=self._make_locator(),
                value=None,
                required=True,
            )

    def test_required_input_with_value_passes(self):
        el = ElementDefinition(
            name="Email",
            type=ElementType.TEXT,
            action=ActionType.INPUT,
            locator=self._make_locator(),
            value="user@example.com",
            required=True,
        )
        assert el.value == "user@example.com"

    def test_click_without_value_is_valid(self):
        el = ElementDefinition(
            name="Btn",
            type=ElementType.BUTTON,
            action=ActionType.CLICK,
            locator=self._make_locator(),
        )
        assert el.value is None

    def test_pre_and_post_wait(self):
        wait = WaitConditionDefinition(
            condition=WaitConditionType.VISIBLE,
            timeout=5,
            locator=self._make_locator(),
        )
        el = ElementDefinition(
            name="Field",
            type=ElementType.TEXT,
            action=ActionType.INPUT,
            locator=self._make_locator(),
            value="test",
            pre_wait=wait,
            post_wait=wait,
        )
        assert el.pre_wait is not None
        assert el.post_wait is not None

    def test_retry_count_bounds(self):
        with pytest.raises(ValidationError):
            ElementDefinition(
                name="X",
                type=ElementType.BUTTON,
                action=ActionType.CLICK,
                locator=self._make_locator(),
                retry_count=11,  # max is 10
            )

    def test_number_and_email_element_types_are_valid(self):
        """ElementType.NUMBER and EMAIL must be accepted by Pydantic validation."""
        for etype in (ElementType.NUMBER, ElementType.EMAIL):
            el = ElementDefinition(
                name="Field",
                type=etype,
                action=ActionType.INPUT,
                locator=self._make_locator(),
                value="test",
            )
            assert el.type == etype

    def test_window_switch_action_types_are_valid(self):
        """Pydantic must accept all three window-switch ActionType values."""
        for atype in (
            ActionType.SWITCH_TO_NEW_WINDOW,
            ActionType.SWITCH_TO_NEW_TAB,
            ActionType.SWITCH_TO_LATEST_WINDOW,
        ):
            el = ElementDefinition(
                name="Win",
                type=ElementType.BUTTON,
                action=atype,
                locator=self._make_locator(),
            )
            assert el.action == atype


# ---------------------------------------------------------------------------
# SectionDefinition
# ---------------------------------------------------------------------------

class TestSectionDefinition:
    def test_empty_section(self):
        sec = SectionDefinition(name="My Section", order=1)
        assert sec.elements == []
        assert sec.repeatable is False

    def test_section_with_locator(self):
        sec = SectionDefinition(
            name="Form",
            order=1,
            locator=LocatorDefinition(by="id", value="form"),
        )
        assert sec.locator is not None


# ---------------------------------------------------------------------------
# PageDefinition
# ---------------------------------------------------------------------------

class TestPageDefinition:
    def test_ordered_sections(self):
        page = PageDefinition(
            name="P",
            order=1,
            sections=[
                SectionDefinition(name="B", order=2),
                SectionDefinition(name="A", order=1),
            ],
        )
        names = [s.name for s in page.ordered_sections]
        assert names == ["A", "B"]

    def test_load_criteria_optional(self):
        page = PageDefinition(name="P", order=1)
        assert page.load_criteria is None


# ---------------------------------------------------------------------------
# WorkflowDefinition
# ---------------------------------------------------------------------------

class TestWorkflowDefinition:
    def _minimal(self):
        return {
            "workflow_name": "Test WF",
            "start_url": "https://example.com",
            "tabs": [],
        }

    @requires_pydantic_v2
    def test_minimal_workflow(self):
        wf = WorkflowDefinition.model_validate(self._minimal())
        assert wf.workflow_name == "Test WF"
        assert wf.tabs == []

    @requires_pydantic_v2
    def test_empty_start_url_raises(self):
        data = self._minimal()
        data["start_url"] = "   "
        with pytest.raises(ValidationError):
            WorkflowDefinition.model_validate(data)

    @requires_pydantic_v2
    def test_ordered_tabs(self):
        data = self._minimal()
        data["tabs"] = [
            {"name": "Z", "order": 3, "pages": []},
            {"name": "A", "order": 1, "pages": []},
            {"name": "M", "order": 2, "pages": []},
        ]
        wf = WorkflowDefinition.model_validate(data)
        names = [t.name for t in wf.ordered_tabs]
        assert names == ["A", "M", "Z"]

    @requires_pydantic_v2
    def test_metadata_optional(self):
        wf = WorkflowDefinition.model_validate(self._minimal())
        assert wf.metadata is None

    @requires_pydantic_v2
    def test_description_optional(self):
        wf = WorkflowDefinition.model_validate(self._minimal())
        assert wf.description is None


# ---------------------------------------------------------------------------
# LoadCriteria defaults
# ---------------------------------------------------------------------------

class TestLoadCriteria:
    def test_defaults(self):
        lc = LoadCriteria()
        assert lc.timeout == 20
        assert lc.require_document_ready is True
        assert lc.require_ajax_idle is False

    def test_with_locator(self):
        lc = LoadCriteria(
            condition=WaitConditionType.VISIBLE,
            locator=LocatorDefinition(by="id", value="form"),
            timeout=30,
        )
        assert lc.locator is not None
        assert lc.timeout == 30
