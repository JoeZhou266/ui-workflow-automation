"""Unit tests for WorkflowLoader — no browser required."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.core.exceptions import WorkflowValidationError
from src.data.json_loader import WorkflowLoader, resolve_refs


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

    def test_load_resolves_tab_ref(self, tmp_path):
        tab_data = {"name": "Account", "order": 1, "pages": []}
        tabs_dir = tmp_path / "tabs"
        tabs_dir.mkdir()
        (tabs_dir / "account_tab.json").write_text(json.dumps(tab_data), encoding="utf-8")

        workflow_data = {
            "workflow_name": "Onboarding",
            "start_url": "https://example.com",
            "tabs": [{"$ref": "tabs/account_tab.json"}],
        }
        wf_path = tmp_path / "workflow.json"
        wf_path.write_text(json.dumps(workflow_data), encoding="utf-8")

        wf = WorkflowLoader.load(wf_path)
        assert len(wf.tabs) == 1
        assert wf.tabs[0].name == "Account"

    def test_load_raw_resolves_refs(self, tmp_path):
        tab_data = {"name": "Account", "order": 1, "pages": []}
        tabs_dir = tmp_path / "tabs"
        tabs_dir.mkdir()
        (tabs_dir / "account_tab.json").write_text(json.dumps(tab_data), encoding="utf-8")

        workflow_data = {
            "workflow_name": "Onboarding",
            "start_url": "https://example.com",
            "tabs": [{"$ref": "tabs/account_tab.json"}],
        }
        wf_path = tmp_path / "workflow.json"
        wf_path.write_text(json.dumps(workflow_data), encoding="utf-8")

        raw = WorkflowLoader.load_raw(wf_path)
        assert raw["tabs"][0]["name"] == "Account"

    def test_load_nested_ref_fixture(self):
        fixture = Path(__file__).parent.parent.parent / "testdata/workflows/nested_ref_workflow.json"
        wf = WorkflowLoader.load(fixture)
        assert wf.workflow_name == "Onboarding"
        assert len(wf.tabs) == 2
        assert wf.tabs[0].name == "Account"
        account_sections = wf.tabs[0].pages[0].sections
        assert account_sections[0].name == "Personal Info"
        assert account_sections[1].name == "Address"
        assert wf.tabs[1].name == "Summary"
        assert wf.tabs[1].pages[0].name == "Summary Page"


class TestResolveRefs:
    def test_no_refs_returns_data_unchanged(self, tmp_path):
        data = {"workflow_name": "Test", "tabs": []}
        result = resolve_refs(data, tmp_path)
        assert result == data

    def test_resolves_ref_in_dict(self, tmp_path):
        tab_data = {"name": "Account", "pages": []}
        (tmp_path / "account_tab.json").write_text(json.dumps(tab_data), encoding="utf-8")

        data = {"$ref": "account_tab.json"}
        result = resolve_refs(data, tmp_path)
        assert result == tab_data

    def test_resolves_ref_in_list(self, tmp_path):
        tab_data = {"name": "Account", "pages": []}
        (tmp_path / "account_tab.json").write_text(json.dumps(tab_data), encoding="utf-8")

        data = {"tabs": [{"$ref": "account_tab.json"}, {"name": "Summary", "pages": []}]}
        result = resolve_refs(data, tmp_path)
        assert result == {
            "tabs": [
                {"name": "Account", "pages": []},
                {"name": "Summary", "pages": []},
            ]
        }

    def test_resolves_nested_refs(self, tmp_path):
        sections_dir = tmp_path / "sections"
        sections_dir.mkdir()
        section_data = {"name": "Personal Info", "fields": ["first_name", "last_name"]}
        (sections_dir / "personal_info.json").write_text(
            json.dumps(section_data), encoding="utf-8"
        )

        tabs_dir = tmp_path / "tabs"
        tabs_dir.mkdir()
        tab_data = {
            "name": "Account",
            "pages": [
                {
                    "name": "Profile",
                    "sections": [
                        {"$ref": "../sections/personal_info.json"},
                        {"name": "Address"},
                    ],
                }
            ],
        }
        (tabs_dir / "account_tab.json").write_text(json.dumps(tab_data), encoding="utf-8")

        data = {"tabs": [{"$ref": "tabs/account_tab.json"}]}
        result = resolve_refs(data, tmp_path)

        assert result == {
            "tabs": [
                {
                    "name": "Account",
                    "pages": [
                        {
                            "name": "Profile",
                            "sections": [
                                {"name": "Personal Info", "fields": ["first_name", "last_name"]},
                                {"name": "Address"},
                            ],
                        }
                    ],
                }
            ]
        }

    def test_missing_ref_raises_file_not_found(self, tmp_path):
        data = {"$ref": "nonexistent.json"}
        with pytest.raises(FileNotFoundError, match="nonexistent.json"):
            resolve_refs(data, tmp_path)

    def test_circular_ref_raises_value_error(self, tmp_path):
        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        a.write_text(json.dumps({"$ref": "b.json"}), encoding="utf-8")
        b.write_text(json.dumps({"$ref": "a.json"}), encoding="utf-8")

        data = {"$ref": "a.json"}
        with pytest.raises(ValueError, match="Circular"):
            resolve_refs(data, tmp_path)
