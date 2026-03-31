from __future__ import annotations


class FrameworkError(Exception):
    """Base class for all framework exceptions."""


class WorkflowValidationError(FrameworkError):
    """Raised when a workflow JSON file fails schema or semantic validation."""

    def __init__(self, message: str, path: str = "") -> None:
        location = f" [file: {path}]" if path else ""
        super().__init__(f"Workflow validation error{location}: {message}")
        self.path = path


class LocatorResolutionError(FrameworkError):
    """Raised when a locator `by` string cannot be mapped to a Selenium By value."""

    def __init__(self, by: str, element_name: str = "") -> None:
        context = f" for element '{element_name}'" if element_name else ""
        super().__init__(f"Unknown locator strategy '{by}'{context}")
        self.by = by
        self.element_name = element_name


class ElementActionError(FrameworkError):
    """Raised when a browser interaction with an element fails."""

    def __init__(self, message: str, element_name: str = "", action: str = "") -> None:
        parts = []
        if element_name:
            parts.append(f"element='{element_name}'")
        if action:
            parts.append(f"action='{action}'")
        context = f" ({', '.join(parts)})" if parts else ""
        super().__init__(f"Element action failed{context}: {message}")
        self.element_name = element_name
        self.action = action


class PageLoadError(FrameworkError):
    """Raised when a page fails to reach its defined readiness state."""

    def __init__(self, message: str, page_name: str = "", tab_name: str = "") -> None:
        location_parts = []
        if tab_name:
            location_parts.append(f"tab='{tab_name}'")
        if page_name:
            location_parts.append(f"page='{page_name}'")
        context = f" ({', '.join(location_parts)})" if location_parts else ""
        super().__init__(f"Page load failed{context}: {message}")
        self.page_name = page_name
        self.tab_name = tab_name


class WaitTimeoutError(FrameworkError):
    """Raised when an explicit wait condition times out."""

    def __init__(self, condition: str, timeout: float, context: str = "") -> None:
        ctx = f" | context: {context}" if context else ""
        super().__init__(
            f"Wait timed out after {timeout}s waiting for '{condition}'{ctx}"
        )
        self.condition = condition
        self.timeout = timeout


class WorkflowExecutionError(FrameworkError):
    """Raised when the workflow engine encounters an unrecoverable error."""

    def __init__(
        self,
        message: str,
        workflow_name: str = "",
        tab: str = "",
        page: str = "",
        section: str = "",
        element: str = "",
    ) -> None:
        parts = []
        if workflow_name:
            parts.append(f"workflow='{workflow_name}'")
        if tab:
            parts.append(f"tab='{tab}'")
        if page:
            parts.append(f"page='{page}'")
        if section:
            parts.append(f"section='{section}'")
        if element:
            parts.append(f"element='{element}'")
        context = f" [{', '.join(parts)}]" if parts else ""
        super().__init__(f"Workflow execution error{context}: {message}")
