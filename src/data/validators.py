from __future__ import annotations

from typing import List

from src.core.exceptions import WorkflowValidationError
from src.core.logger import get_logger
from src.models.workflow_models import WorkflowDefinition

logger = get_logger("validators")


class WorkflowValidator:
    """Performs semantic validation on a fully-parsed :class:`WorkflowDefinition`."""

    def validate(self, definition: WorkflowDefinition) -> List[str]:
        """Run all validation rules and return a list of error messages.

        An empty list means the definition is valid.
        """
        errors: List[str] = []
        errors.extend(self._check_start_url(definition))
        errors.extend(self._check_tab_orders_unique(definition))
        errors.extend(self._check_page_orders(definition))
        errors.extend(self._check_section_orders(definition))
        errors.extend(self._check_element_names_unique(definition))
        return errors

    def validate_or_raise(self, definition: WorkflowDefinition) -> None:
        """Validate and raise :class:`WorkflowValidationError` if any errors exist."""
        errors = self.validate(definition)
        if errors:
            combined = "\n  - ".join(errors)
            raise WorkflowValidationError(
                f"Workflow '{definition.workflow_name}' has {len(errors)} validation error(s):\n  - {combined}"
            )
        logger.debug("Workflow '%s' passed semantic validation", definition.workflow_name)

    # ------------------------------------------------------------------
    # Private validation rules
    # ------------------------------------------------------------------

    @staticmethod
    def _check_start_url(definition: WorkflowDefinition) -> List[str]:
        errors = []
        if not definition.start_url.startswith(("http://", "https://", "/")):
            errors.append(
                f"start_url '{definition.start_url}' does not look like a valid URL or path"
            )
        return errors

    @staticmethod
    def _check_tab_orders_unique(definition: WorkflowDefinition) -> List[str]:
        orders = [t.order for t in definition.tabs]
        if len(orders) != len(set(orders)):
            return ["Duplicate tab 'order' values detected"]
        return []

    @staticmethod
    def _check_page_orders(definition: WorkflowDefinition) -> List[str]:
        errors = []
        for tab in definition.tabs:
            orders = [p.order for p in tab.pages]
            if len(orders) != len(set(orders)):
                errors.append(f"Tab '{tab.name}' has duplicate page 'order' values")
        return errors

    @staticmethod
    def _check_section_orders(definition: WorkflowDefinition) -> List[str]:
        errors = []
        for tab in definition.tabs:
            for page in tab.pages:
                orders = [s.order for s in page.sections]
                if len(orders) != len(set(orders)):
                    errors.append(
                        f"Tab '{tab.name}' > Page '{page.name}' has duplicate section 'order' values"
                    )
        return errors

    @staticmethod
    def _check_element_names_unique(definition: WorkflowDefinition) -> List[str]:
        errors = []
        for tab in definition.tabs:
            for page in tab.pages:
                for section in page.sections:
                    names = [e.name for e in section.elements]
                    if len(names) != len(set(names)):
                        errors.append(
                            f"Tab '{tab.name}' > Page '{page.name}' > Section '{section.name}' "
                            "has duplicate element names"
                        )
        return errors
