from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.constants import MAX_INDEX_SPAN, RESERVED_PARAM_NAMES
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
    # None means single-element / no loop (D-01); existing JSON deserializes unchanged.
    # `value` deliberately stays Optional[Any] so a future per-index value list is an
    # additive, backward-compatible change (D-06 — not implemented now).
    index_range: Optional[List[int]] = None

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

    @model_validator(mode="after")
    def validate_index_range(self) -> ElementDefinition:
        # mode="after" (not field_validator) because the messages reference self.name (Pitfall 6).
        if self.index_range is None:
            return self
        if len(self.index_range) != 2:
            raise ValueError(
                f"Element '{self.name}' index_range must be a 2-element [start, end] "
                f"list; got {self.index_range!r}."
            )
        start, end = self.index_range
        # WR-01: reject negative start — negative DOM indices/ids are almost never
        # intended and would silently produce names like 'amount_-1' targeting
        # nonexistent elements (N confusing failures instead of one clear error).
        if start < 0:
            raise ValueError(
                f"Element '{self.name}' index_range start ({start}) must be >= 0."
            )
        if start > end:
            raise ValueError(
                f"Element '{self.name}' index_range start ({start}) must be <= end ({end})."
            )
        # WR-02: bound the span so a JSON typo (e.g. [0, 1000000]) fails loud at load
        # time instead of generating a million model_copy/StepResult records at runtime.
        span = end - start + 1
        if span > MAX_INDEX_SPAN:
            raise ValueError(
                f"Element '{self.name}' index_range spans {span} indices; "
                f"maximum is {MAX_INDEX_SPAN}."
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


class ParameterDefinition(BaseModel):
    """A named string parameter declared at the workflow root level.

    Parameter values may contain ``${env:KEY}`` placeholders resolved at load
    time before condition evaluation.
    """

    name: str = Field(..., description="Parameter name referenced in conditions as ${name}")
    value: str = Field(..., description="Parameter value; may contain ${env:KEY} tokens")


class WorkflowDefinition(BaseModel):
    """Root model for a complete workflow JSON definition."""

    workflow_name: str
    description: Optional[str] = None
    start_url: str
    tabs: List[TabDefinition] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    parameters: Optional[List[ParameterDefinition]] = None

    @field_validator("start_url")
    @classmethod
    def start_url_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("start_url must not be empty")
        return v

    @model_validator(mode="after")
    def reject_reserved_param_names(self) -> WorkflowDefinition:
        # CR-01: enforce the reserved-name invariant at the model boundary so EVERY
        # construction path is covered — model_validate (loader), direct
        # WorkflowDefinition(...) construction, and the engine constructor alike.
        # A param named 'index' would otherwise be silently overwritten by the loop
        # counter in WorkflowEngine._run_section's per-iteration merge. The loader's
        # string-level check remains as an earlier/clearer error for JSON input.
        for p in (self.parameters or []):
            if p.name in RESERVED_PARAM_NAMES:
                raise ValueError(
                    f"Workflow parameter name '{p.name}' is reserved for "
                    "index_range loop expansion and cannot be used as a "
                    "workflow parameter."
                )
        return self

    @property
    def ordered_tabs(self) -> List[TabDefinition]:
        return sorted(self.tabs, key=lambda t: t.order)
