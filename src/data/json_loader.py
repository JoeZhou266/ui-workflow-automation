from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from src.actions.value_resolver import resolve_dynamic_value
from src.core.exceptions import WorkflowValidationError
from src.core.logger import get_logger
from src.data.condition_evaluator import evaluate_condition
from src.models.workflow_models import WorkflowDefinition

logger = get_logger("json_loader")


def resolve_refs(
    data: object,
    base_dir: Path,
    _resolving: frozenset = frozenset(),
    params: dict = {},
) -> object:
    """Recursively resolve ``{"$ref": "<path>"}`` nodes in *data*.

    Args:
        data: Parsed JSON value (dict, list, or scalar).
        base_dir: Directory used to resolve relative ``$ref`` paths.
        _resolving: Absolute paths currently on the resolution call stack
            (used to detect circular references).
        params: Workflow parameters dict (name -> resolved value string) used
            to evaluate ``condition`` sibling keys on ``$ref`` nodes.

    Returns:
        The fully resolved data structure. Returns ``None`` when a list item's
        ``$ref`` node carries a condition that evaluates to false (caller must
        filter ``None`` out of parent lists).

    Raises:
        FileNotFoundError: If a referenced file does not exist.
        ValueError: If a circular reference is detected.
        WorkflowValidationError: If a condition references an undefined parameter.
    """
    if isinstance(data, dict):
        if "$ref" in data:
            ref_path = (base_dir / data["$ref"]).resolve()
            if ref_path in _resolving:
                raise ValueError(
                    f"Circular $ref detected: {ref_path}"
                )
            if not ref_path.exists():
                raise FileNotFoundError(
                    f"$ref target not found: {ref_path}"
                )
            # Evaluate condition sibling key before loading the referenced file.
            # This is the only sibling key on a $ref node that is acted upon
            # (all others remain ignored per Phase 1 full-replacement rule).
            condition = data.get("condition")
            if condition is not None:
                if not evaluate_condition(condition, params):
                    return None  # Sentinel: caller (list branch) filters this out
            raw = ref_path.read_text(encoding="utf-8")
            loaded = json.loads(raw)
            return resolve_refs(loaded, ref_path.parent, _resolving | {ref_path}, params)
        return {k: resolve_refs(v, base_dir, _resolving, params) for k, v in data.items()}
    if isinstance(data, list):
        resolved = [resolve_refs(item, base_dir, _resolving, params) for item in data]
        return [item for item in resolved if item is not None]
    return data


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

        # Extract workflow parameters from raw JSON before $ref resolution.
        # Resolve ${env:KEY} in each parameter value at load time (D-07).
        params: dict = {}
        raw_params = data.get("parameters") if isinstance(data, dict) else None
        if raw_params:
            for p in raw_params:
                resolved_value = resolve_dynamic_value(p["value"])
                params[p["name"]] = resolved_value

        try:
            data = resolve_refs(data, file_path.parent, params=params)
        except (FileNotFoundError, ValueError) as exc:
            raise WorkflowValidationError(str(exc), path=str_path) from exc
        except WorkflowValidationError:
            raise  # Already a WorkflowValidationError — re-raise as-is

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
        """Load a JSON file, resolve $ref references, and return the raw dict."""
        file_path = Path(path)
        try:
            raw = file_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            params: dict = {}
            raw_params = data.get("parameters") if isinstance(data, dict) else None
            if raw_params:
                for p in raw_params:
                    resolved_value = resolve_dynamic_value(p["value"])
                    params[p["name"]] = resolved_value
            return resolve_refs(data, file_path.parent, params=params)
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowValidationError(str(exc), path=str(file_path)) from exc
