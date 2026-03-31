from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExecutionContext:
    """Tracks the current position in the workflow hierarchy during execution.

    Passed through the engine so every component has access to location
    context for logging and error messages.
    """

    workflow_name: str
    tab_name: str = ""
    page_name: str = ""
    section_name: str = ""
    element_name: str = ""

    def at_tab(self, tab: str) -> ExecutionContext:
        return ExecutionContext(
            workflow_name=self.workflow_name,
            tab_name=tab,
        )

    def at_page(self, page: str) -> ExecutionContext:
        return ExecutionContext(
            workflow_name=self.workflow_name,
            tab_name=self.tab_name,
            page_name=page,
        )

    def at_section(self, section: str) -> ExecutionContext:
        return ExecutionContext(
            workflow_name=self.workflow_name,
            tab_name=self.tab_name,
            page_name=self.page_name,
            section_name=section,
        )

    def at_element(self, element: str) -> ExecutionContext:
        return ExecutionContext(
            workflow_name=self.workflow_name,
            tab_name=self.tab_name,
            page_name=self.page_name,
            section_name=self.section_name,
            element_name=element,
        )

    def __str__(self) -> str:
        parts = [self.workflow_name]
        for part in [self.tab_name, self.page_name, self.section_name, self.element_name]:
            if part:
                parts.append(part)
        return " > ".join(parts)
