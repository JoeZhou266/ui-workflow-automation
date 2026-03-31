from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.enums import ActionType, ElementType, WaitConditionType


class LocatorDefinition(BaseModel):
    """Maps to a Selenium ``By`` strategy and its target value."""

    by: str = Field(..., description="Locator strategy: id, name, css_selector, xpath, etc.")
    value: str = Field(..., description="Locator value / selector string")

    @field_validator("by")
    @classmethod
    def by_must_be_known(cls, v: str) -> str:
        allowed = {
            "id", "name", "class_name", "css_selector",
            "xpath", "link_text", "partial_link_text", "tag_name",
        }
        if v not in allowed:
            raise ValueError(f"Unknown locator strategy '{v}'. Allowed: {sorted(allowed)}")
        return v


class WaitConditionDefinition(BaseModel):
    """Describes an explicit wait to perform before or after an element action."""

    condition: WaitConditionType
    timeout: int = Field(default=10, ge=1, le=300)
    poll_frequency_ms: int = Field(default=500, ge=50, le=5000)
    locator: Optional[LocatorDefinition] = None
    text_expected: Optional[str] = None
    attribute_name: Optional[str] = None
    attribute_value: Optional[str] = None
    minimum_count: Optional[int] = None
    require_document_ready: bool = False
    require_ajax_idle: bool = False
    spinner_locator: Optional[LocatorDefinition] = None
    overlay_locator: Optional[LocatorDefinition] = None


class AssertionDefinition(BaseModel):
    """Optional post-action verification step."""

    condition: WaitConditionType
    locator: Optional[LocatorDefinition] = None
    text_expected: Optional[str] = None
    attribute_name: Optional[str] = None
    attribute_value: Optional[str] = None
    url_fragment: Optional[str] = None
    timeout: int = Field(default=5, ge=1, le=60)


class LoadCriteria(BaseModel):
    """Defines how the workflow engine determines that a page is ready."""

    condition: Optional[WaitConditionType] = WaitConditionType.VISIBLE
    locator: Optional[LocatorDefinition] = None
    timeout: int = Field(default=20, ge=1, le=300)
    require_document_ready: bool = True
    require_ajax_idle: bool = False
    spinner_locator: Optional[LocatorDefinition] = None
    overlay_locator: Optional[LocatorDefinition] = None
    text_expected: Optional[str] = None
    attribute_name: Optional[str] = None
    attribute_value: Optional[str] = None
    minimum_count: Optional[int] = None


class ElementDefinition(BaseModel):
    """Describes a single UI element and the action to perform on it."""

    name: str
    type: ElementType
    action: ActionType
    locator: LocatorDefinition
    value: Optional[Any] = None
    required: bool = False
    wait_condition: Optional[WaitConditionDefinition] = None
    pre_wait: Optional[WaitConditionDefinition] = None
    post_wait: Optional[WaitConditionDefinition] = None
    options: Optional[Dict[str, Any]] = None
    assertions: Optional[List[AssertionDefinition]] = None
    retryable: bool = False
    retry_count: int = Field(default=0, ge=0, le=10)

    @model_validator(mode="after")
    def value_required_for_input_actions(self) -> ElementDefinition:
        input_actions = {ActionType.INPUT, ActionType.SELECT_BY_TEXT,
                         ActionType.SELECT_BY_VALUE, ActionType.SELECT_BY_INDEX,
                         ActionType.UPLOAD}
        if self.action in input_actions and self.value is None and self.required:
            raise ValueError(
                f"Element '{self.name}' has action '{self.action}' and required=true "
                "but no value is provided."
            )
        return self


class SectionDefinition(BaseModel):
    """A logical grouping of UI elements within a page."""

    name: str
    order: int = Field(default=1, ge=1)
    locator: Optional[LocatorDefinition] = None
    repeatable: bool = False
    elements: List[ElementDefinition] = Field(default_factory=list)


class PageDefinition(BaseModel):
    """A single navigable page within a tab."""

    name: str
    order: int = Field(default=1, ge=1)
    path: Optional[str] = None
    load_criteria: Optional[LoadCriteria] = None
    sections: List[SectionDefinition] = Field(default_factory=list)

    @property
    def ordered_sections(self) -> List[SectionDefinition]:
        return sorted(self.sections, key=lambda s: s.order)


class TabDefinition(BaseModel):
    """A high-level tab grouping one or more pages."""

    name: str
    order: int = Field(default=1, ge=1)
    pages: List[PageDefinition] = Field(default_factory=list)

    @property
    def ordered_pages(self) -> List[PageDefinition]:
        return sorted(self.pages, key=lambda p: p.order)


class WorkflowDefinition(BaseModel):
    """Root model for a complete workflow JSON definition."""

    workflow_name: str
    description: Optional[str] = None
    start_url: str
    tabs: List[TabDefinition] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("start_url")
    @classmethod
    def start_url_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("start_url must not be empty")
        return v

    @property
    def ordered_tabs(self) -> List[TabDefinition]:
        return sorted(self.tabs, key=lambda t: t.order)
