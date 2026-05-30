"""Unit tests for workflow parameters and conditional $ref resolution — no browser required."""
from __future__ import annotations

import json
from pathlib import Path

import pydantic
import pytest

from src.core.exceptions import WorkflowValidationError
from src.data.condition_evaluator import evaluate_condition
from src.data.json_loader import WorkflowLoader
from src.models.workflow_models import ParameterDefinition, WorkflowDefinition

# Pydantic v2 guard (same pattern as test_workflow_models.py)
_PYDANTIC_V2 = int(pydantic.VERSION.split(".")[0]) >= 2
requires_pydantic_v2 = pytest.mark.skipif(
    not _PYDANTIC_V2, reason="Pydantic v2 required for model_validate"
)


class TestParameterDefinition:
    """SC-01: WorkflowDefinition.parameters accepts a list of {name, value} objects."""

    @requires_pydantic_v2
    def test_parameter_definition_valid(self):
        p = ParameterDefinition(name="account_type", value="OPEN")
        assert p.name == "account_type"
        assert p.value == "OPEN"

    @requires_pydantic_v2
    def test_workflow_definition_accepts_parameters(self):
        wf = WorkflowDefinition.model_validate({
            "workflow_name": "Test WF",
            "start_url": "https://example.com",
            "parameters": [{"name": "account_type", "value": "OPEN"}],
            "tabs": [],
        })
        assert wf.parameters is not None
        assert len(wf.parameters) == 1
        assert wf.parameters[0].name == "account_type"
        assert wf.parameters[0].value == "OPEN"

    @requires_pydantic_v2
    def test_workflow_definition_no_parameters_defaults_to_none(self):
        wf = WorkflowDefinition.model_validate({
            "workflow_name": "Test WF",
            "start_url": "https://example.com",
            "tabs": [],
        })
        assert wf.parameters is None


class TestEvaluateCondition:
    """SC-02 / SC-04 / SC-07: evaluate_condition() handles == and != operators and undefined params."""

    def test_eq_true(self):
        assert evaluate_condition("${account_type} == 'OPEN'", {"account_type": "OPEN"}) is True

    def test_eq_false(self):
        assert evaluate_condition("${account_type} == 'OPEN'", {"account_type": "CLOSED"}) is False

    def test_ne_true(self):
        assert evaluate_condition("${account_type} != 'OPEN'", {"account_type": "CLOSED"}) is True

    def test_ne_false(self):
        assert evaluate_condition("${account_type} != 'OPEN'", {"account_type": "OPEN"}) is False

    def test_undefined_param_raises(self):
        with pytest.raises(WorkflowValidationError, match="missing"):
            evaluate_condition("${missing} == 'x'", {})

    def test_malformed_condition_raises(self):
        with pytest.raises(WorkflowValidationError, match="Malformed"):
            evaluate_condition("bad condition", {})


class TestConditionalRef:
    """SC-02/SC-03/SC-04/SC-05/SC-06: Integration tests via WorkflowLoader.load()."""

    def _write_json(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data), encoding="utf-8")

    def _make_tab_file(self, tmp_path: Path, name: str) -> Path:
        tabs_dir = tmp_path / "tabs"
        tabs_dir.mkdir(exist_ok=True)
        tab_path = tabs_dir / f"{name}.json"
        tab_data = {"name": name, "order": 1, "pages": []}
        tab_path.write_text(json.dumps(tab_data), encoding="utf-8")
        return tab_path

    def test_condition_true_includes_tab(self, tmp_path):
        """SC-02, SC-03: Tab with true condition is included."""
        self._make_tab_file(tmp_path, "Summary")
        workflow = {
            "workflow_name": "Onboarding",
            "start_url": "https://example.com",
            "parameters": [{"name": "account_type", "value": "OPEN"}],
            "tabs": [
                {"$ref": "tabs/Summary.json", "condition": "${account_type} == 'OPEN'"}
            ],
        }
        wf_path = tmp_path / "workflow.json"
        self._write_json(wf_path, workflow)
        wf = WorkflowLoader.load(wf_path)
        assert len(wf.tabs) == 1
        assert wf.tabs[0].name == "Summary"

    def test_condition_false_omits_tab(self, tmp_path):
        """SC-03: Tab with false condition is silently omitted."""
        self._make_tab_file(tmp_path, "Summary")
        workflow = {
            "workflow_name": "Onboarding",
            "start_url": "https://example.com",
            "parameters": [{"name": "account_type", "value": "CLOSED"}],
            "tabs": [
                {"$ref": "tabs/Summary.json", "condition": "${account_type} == 'OPEN'"}
            ],
        }
        wf_path = tmp_path / "workflow.json"
        self._write_json(wf_path, workflow)
        wf = WorkflowLoader.load(wf_path)
        assert len(wf.tabs) == 0

    def test_no_condition_resolves_unchanged(self, tmp_path):
        """SC-06: $ref without condition resolves normally (backwards compat)."""
        self._make_tab_file(tmp_path, "Account")
        workflow = {
            "workflow_name": "Onboarding",
            "start_url": "https://example.com",
            "tabs": [{"$ref": "tabs/Account.json"}],
        }
        wf_path = tmp_path / "workflow.json"
        self._write_json(wf_path, workflow)
        wf = WorkflowLoader.load(wf_path)
        assert len(wf.tabs) == 1
        assert wf.tabs[0].name == "Account"

    def test_undefined_param_raises_at_load(self, tmp_path):
        """SC-04: Undefined parameter name raises WorkflowValidationError at load time."""
        self._make_tab_file(tmp_path, "Summary")
        workflow = {
            "workflow_name": "Onboarding",
            "start_url": "https://example.com",
            "parameters": [],  # empty — 'account_type' not declared
            "tabs": [
                {"$ref": "tabs/Summary.json", "condition": "${account_type} == 'OPEN'"}
            ],
        }
        wf_path = tmp_path / "workflow.json"
        self._write_json(wf_path, workflow)
        with pytest.raises(WorkflowValidationError, match="account_type"):
            WorkflowLoader.load(wf_path)

    def test_env_placeholder_in_param_value(self, tmp_path):
        """SC-05: ${env:KEY} in parameter value resolved before condition evaluation."""
        from src.actions.value_resolver import configure_env_resolver
        configure_env_resolver({"ACCT_TYPE": "OPEN"})
        try:
            self._make_tab_file(tmp_path, "Summary")
            workflow = {
                "workflow_name": "Onboarding",
                "start_url": "https://example.com",
                "parameters": [{"name": "account_type", "value": "${env:ACCT_TYPE}"}],
                "tabs": [
                    {"$ref": "tabs/Summary.json", "condition": "${account_type} == 'OPEN'"}
                ],
            }
            wf_path = tmp_path / "workflow.json"
            self._write_json(wf_path, workflow)
            wf = WorkflowLoader.load(wf_path)
            assert len(wf.tabs) == 1
            assert wf.tabs[0].name == "Summary"
        finally:
            configure_env_resolver({})  # Reset env resolver state after test
