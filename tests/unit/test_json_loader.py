"""Unit tests for WorkflowLoader — no browser required."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.core.exceptions import WorkflowValidationError
from src.data.json_loader import WorkflowLoader


VALID_WORKFLOW = {
    "workflow_name": "Test",
    "start_url": "https://example.com",
    "tabs": [],
}


class TestWorkflowLoader:
    def _write_json(self, tmp_path: Path, data: dict) -> Path:
        f = tmp_path / "workflow.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        return f

    def test_load_valid_file(self, tmp_path):
        path = self._write_json(tmp_path, VALID_WORKFLOW)
        definition = WorkflowLoader.load(path)
        assert definition.workflow_name == "Test"
        assert definition.start_url == "https://example.com"

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(WorkflowValidationError, match="File not found"):
            WorkflowLoader.load(tmp_path / "does_not_exist.json")

    def test_load_invalid_json_raises(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{not valid json}", encoding="utf-8")
        with pytest.raises(WorkflowValidationError, match="Invalid JSON"):
            WorkflowLoader.load(f)

    def test_load_non_object_json_raises(self, tmp_path):
        f = tmp_path / "array.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(WorkflowValidationError, match="root must be an object"):
            WorkflowLoader.load(f)

    def test_load_missing_required_field_raises(self, tmp_path):
        # Missing start_url
        data = {"workflow_name": "No URL", "tabs": []}
        path = self._write_json(tmp_path, data)
        with pytest.raises(WorkflowValidationError):
            WorkflowLoader.load(path)

    def test_load_raw_returns_dict(self, tmp_path):
        path = self._write_json(tmp_path, VALID_WORKFLOW)
        raw = WorkflowLoader.load_raw(path)
        assert isinstance(raw, dict)
        assert raw["workflow_name"] == "Test"

    def test_load_with_full_structure(self, tmp_path):
        data = {
            "workflow_name": "Full",
            "start_url": "https://example.com",
            "tabs": [
                {
                    "name": "Tab1",
                    "order": 1,
                    "pages": [
                        {
                            "name": "Page1",
                            "order": 1,
                            "sections": [
                                {
                                    "name": "Sec1",
                                    "order": 1,
                                    "elements": [
                                        {
                                            "name": "El1",
                                            "type": "button",
                                            "action": "click",
                                            "locator": {"by": "id", "value": "btn"},
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        path = self._write_json(tmp_path, data)
        wf = WorkflowLoader.load(path)
        assert len(wf.tabs) == 1
        assert wf.tabs[0].pages[0].sections[0].elements[0].name == "El1"

    def test_load_accepts_string_path(self, tmp_path):
        path = self._write_json(tmp_path, VALID_WORKFLOW)
        wf = WorkflowLoader.load(str(path))  # str, not Path
        assert wf.workflow_name == "Test"
