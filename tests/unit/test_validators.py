"""Unit tests for WorkflowValidator semantic checks — no browser required."""
from __future__ import annotations

import pytest

from src.core.exceptions import WorkflowValidationError
from src.data.validators import WorkflowValidator
from src.models.workflow_models import (
    ElementDefinition,
    LocatorDefinition,
    PageDefinition,
    SectionDefinition,
    TabDefinition,
    WorkflowDefinition,
)
from src.core.enums import ActionType, ElementType


def _make_workflow(**overrides) -> WorkflowDefinition:
    defaults = dict(workflow_name="WF", start_url="https://example.com", tabs=[])
    defaults.update(overrides)
    return WorkflowDefinition.model_validate(defaults)


def _make_tab(name: str, order: int, pages=None) -> TabDefinition:
    return TabDefinition(name=name, order=order, pages=pages or [])


def _make_page(name: str, order: int, sections=None) -> PageDefinition:
    return PageDefinition(name=name, order=order, sections=sections or [])


def _make_section(name: str, order: int, elements=None) -> SectionDefinition:
    return SectionDefinition(name=name, order=order, elements=elements or [])


def _make_element(name: str) -> ElementDefinition:
    return ElementDefinition(
        name=name,
        type=ElementType.BUTTON,
        action=ActionType.CLICK,
        locator=LocatorDefinition(by="id", value="x"),
    )


class TestWorkflowValidator:
    def setup_method(self):
        self.validator = WorkflowValidator()

    def test_valid_workflow_no_errors(self):
        wf = _make_workflow()
        errors = self.validator.validate(wf)
        assert errors == []

    def test_validate_or_raise_clean_workflow(self):
        wf = _make_workflow()
        self.validator.validate_or_raise(wf)  # should not raise

    def test_invalid_start_url_raises(self):
        wf = _make_workflow(start_url="not-a-url-at-all")
        errors = self.validator.validate(wf)
        assert any("start_url" in e for e in errors)

    def test_path_start_url_is_valid(self):
        wf = _make_workflow(start_url="/some/path")
        errors = self.validator.validate(wf)
        assert not any("start_url" in e for e in errors)

    def test_duplicate_tab_orders_detected(self):
        wf = _make_workflow(
            tabs=[
                {"name": "A", "order": 1, "pages": []},
                {"name": "B", "order": 1, "pages": []},  # duplicate order
            ]
        )
        errors = self.validator.validate(wf)
        assert any("tab" in e.lower() for e in errors)

    def test_duplicate_page_orders_detected(self):
        tab = _make_tab("T", 1, pages=[
            _make_page("P1", 1),
            _make_page("P2", 1),  # duplicate order
        ])
        wf = WorkflowDefinition(
            workflow_name="WF",
            start_url="https://x.com",
            tabs=[tab],
        )
        errors = self.validator.validate(wf)
        assert any("page" in e.lower() for e in errors)

    def test_duplicate_section_orders_detected(self):
        page = _make_page("P", 1, sections=[
            _make_section("S1", 1),
            _make_section("S2", 1),  # duplicate order
        ])
        tab = _make_tab("T", 1, pages=[page])
        wf = WorkflowDefinition(
            workflow_name="WF", start_url="https://x.com", tabs=[tab]
        )
        errors = self.validator.validate(wf)
        assert any("section" in e.lower() for e in errors)

    def test_duplicate_element_names_detected(self):
        section = _make_section("S", 1, elements=[
            _make_element("Submit"),
            _make_element("Submit"),  # duplicate name
        ])
        page = _make_page("P", 1, sections=[section])
        tab = _make_tab("T", 1, pages=[page])
        wf = WorkflowDefinition(
            workflow_name="WF", start_url="https://x.com", tabs=[tab]
        )
        errors = self.validator.validate(wf)
        assert any("element" in e.lower() for e in errors)

    def test_validate_or_raise_reports_all_errors(self):
        wf = _make_workflow(
            start_url="not-a-url",
            tabs=[
                {"name": "A", "order": 1, "pages": []},
                {"name": "B", "order": 1, "pages": []},
            ],
        )
        with pytest.raises(WorkflowValidationError) as exc_info:
            self.validator.validate_or_raise(wf)
        assert "validation error" in str(exc_info.value).lower()

    def test_unique_orders_no_errors(self):
        wf = _make_workflow(
            tabs=[
                {"name": "A", "order": 1, "pages": []},
                {"name": "B", "order": 2, "pages": []},
                {"name": "C", "order": 3, "pages": []},
            ]
        )
        errors = self.validator.validate(wf)
        assert errors == []
