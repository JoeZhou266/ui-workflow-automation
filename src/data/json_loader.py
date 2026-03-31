from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from src.core.exceptions import WorkflowValidationError
from src.core.logger import get_logger
from src.models.workflow_models import WorkflowDefinition

logger = get_logger("json_loader")


class WorkflowLoader:
    """Loads and parses a workflow JSON file into a :class:`WorkflowDefinition`."""

    @staticmethod
    def load(path: Union[str, Path]) -> WorkflowDefinition:
        """Load, parse, and validate a workflow JSON file.

        Args:
            path: Filesystem path to the ``.json`` workflow file.

        Returns:
            A validated :class:`WorkflowDefinition` instance.

        Raises:
            WorkflowValidationError: If the file cannot be read, parsed, or validated.
        """
        file_path = Path(path)
        str_path = str(file_path)

        logger.info("Loading workflow from: %s", str_path)

        if not file_path.exists():
            raise WorkflowValidationError(
                f"File not found: {str_path}", path=str_path
            )

        if not file_path.is_file():
            raise WorkflowValidationError(
                f"Path is not a file: {str_path}", path=str_path
            )

        try:
            raw = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise WorkflowValidationError(
                f"Cannot read file: {exc}", path=str_path
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise WorkflowValidationError(
                f"Invalid JSON: {exc}", path=str_path
            ) from exc

        if not isinstance(data, dict):
            raise WorkflowValidationError(
                "Workflow JSON root must be an object", path=str_path
            )

        try:
            from pydantic import ValidationError

            definition = WorkflowDefinition.model_validate(data)
        except Exception as exc:  # pydantic ValidationError
            raise WorkflowValidationError(str(exc), path=str_path) from exc

        logger.info(
            "Loaded workflow '%s' with %d tab(s)",
            definition.workflow_name,
            len(definition.tabs),
        )
        return definition

    @staticmethod
    def load_raw(path: Union[str, Path]) -> dict:
        """Load a JSON file and return the raw dict without model validation."""
        file_path = Path(path)
        try:
            raw = file_path.read_text(encoding="utf-8")
            return json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowValidationError(str(exc), path=str(file_path)) from exc
