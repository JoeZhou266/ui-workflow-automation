"""Unit tests for Phase 22 index_range loop expansion — no browser required.

These are Wave 0 RED tests. All tests fail until Plan 02 implements:
  - ElementDefinition.index_range field
  - WorkflowEngine._run_section expansion loop (index substitution in name + locator)
  - WorkflowLoader reserved-name guard for 'index' parameter

Test strategy:
  - Call WorkflowEngine._run_section directly to avoid navigator/page-load deps
  - Mock driver, WaitManager, and DynamicSection via MagicMock
  - Patch src.actions.action_factory.ActionFactory.run so _run_element's real
    try/except block executes without Selenium
  - Use a real ResultCollector; assert on engine._collector.summary().steps
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest

from src.actions.action_factory import ActionFactory
from src.core.enums import ActionType, ElementType, StepStatus
from src.core.exceptions import ElementActionError, SkipElementSignal
from src.models.workflow_models import (
    ElementDefinition,
    LocatorDefinition,
    SectionDefinition,
    WorkflowDefinition,
)
from src.workflow.execution_context import ExecutionContext
from src.workflow.result_collector import ResultCollector
from src.workflow.workflow_engine import WorkflowEngine


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _make_locator(value: str = "el_${index}") -> LocatorDefinition:
    return LocatorDefinition(by="id", value=value)


def _make_indexed_element(
    name: str = "amount_${index}",
    index_range=None,
    locator: LocatorDefinition | None = None,
    **kwargs,
) -> ElementDefinition:
    return ElementDefinition(
        name=name,
        type=ElementType.NUMBER,
        action=ActionType.INPUT,
        locator=locator if locator is not None else _make_locator(),
        value="100",
        index_range=index_range,
        **kwargs,
    )


def _make_engine() -> WorkflowEngine:
    """Build a WorkflowEngine with a MagicMock driver and minimal workflow definition."""
    driver = MagicMock()
    definition = WorkflowDefinition(
        workflow_name="TestWorkflow",
        start_url="https://example.com",
        tabs=[],
    )
    # Patch WaitManager construction so no real WebDriverWait is created
    with patch("src.workflow.workflow_engine.WaitManager") as mock_wm_cls:
        mock_wm_cls.return_value = MagicMock()
        with patch("src.workflow.workflow_engine.ScreenshotManager"):
            with patch("src.workflow.workflow_engine.BasePage"):
                with patch("src.workflow.workflow_engine.Navigator"):
                    engine = WorkflowEngine(driver=driver, definition=definition)
    return engine


def _run_section_with_patch(engine: WorkflowEngine, section: SectionDefinition, ctx: ExecutionContext, run_side_effect):
    """Run _run_section with ActionFactory.run patched to the given side_effect."""
    with patch("src.actions.action_factory.ActionFactory.run", side_effect=run_side_effect) as mock_run:
        # Also patch DynamicSection so _run_section doesn't fail on section instantiation
        with patch("src.workflow.workflow_engine.DynamicSection"):
            engine._run_section(section, ctx)
    return mock_run


# ---------------------------------------------------------------------------
# TestIndexExpansion
# ---------------------------------------------------------------------------

class TestIndexExpansion:
    """Engine-level tests for index_range loop expansion (D-02a..D-09, no-regression)."""

    def _ctx(self) -> ExecutionContext:
        return ExecutionContext(
            workflow_name="TestWorkflow",
            tab_name="Tab1",
            page_name="Page1",
            section_name="Section1",
        )

    def test_range_0_to_3_produces_four_calls(self):
        """D-02a: index_range=[0, 3] causes ActionFactory.run to be called 4 times."""
        engine = _make_engine()
        element = _make_indexed_element(index_range=[0, 3])
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        mock_run = _run_section_with_patch(engine, section, ctx, run_side_effect=[None, None, None, None])
        assert mock_run.call_count == 4

    def test_embedded_index_in_locator_value(self):
        """D-03: On the index=2 iteration, the element carried into _run_element
        has locator value resolving to 'el_2' (index substituted mid-string).
        Captured via patched ActionFactory.run call_args.
        """
        engine = _make_engine()
        element = _make_indexed_element(
            name="amount_${index}",
            locator=_make_locator("el_${index}"),
            index_range=[0, 3],
        )
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        captured_elements = []

        def capture_run(el):
            captured_elements.append(el)

        with patch("src.workflow.workflow_engine.DynamicSection"):
            with patch("src.actions.action_factory.ActionFactory.run", side_effect=capture_run):
                engine._run_section(section, ctx)

        # The third call (index=2) should have locator value "el_2"
        assert len(captured_elements) == 4
        assert captured_elements[2].locator.value == "el_2"

    def test_xpath_locator_with_index(self):
        """D-03b: XPath locator with embedded ${index} is substituted per iteration."""
        engine = _make_engine()
        element = _make_indexed_element(
            name="amount_${index}",
            locator=LocatorDefinition(by="xpath", value="//input[@id='amount_${index}']"),
            index_range=[0, 2],
        )
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        captured_elements = []

        def capture_run(el):
            captured_elements.append(el)

        with patch("src.workflow.workflow_engine.DynamicSection"):
            with patch("src.actions.action_factory.ActionFactory.run", side_effect=capture_run):
                engine._run_section(section, ctx)

        # Each iteration should have the index substituted into the XPath
        assert len(captured_elements) == 3
        assert captured_elements[0].locator.value == "//input[@id='amount_0']"
        assert captured_elements[1].locator.value == "//input[@id='amount_1']"
        assert captured_elements[2].locator.value == "//input[@id='amount_2']"

    def test_step_result_shows_concrete_name(self):
        """D-04: summary().steps[2].element_name == 'amount_2' (concrete name, not template)."""
        engine = _make_engine()
        element = _make_indexed_element(
            name="amount_${index}",
            index_range=[0, 3],
        )
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        _run_section_with_patch(engine, section, ctx, run_side_effect=[None, None, None, None])

        steps = engine._collector.summary().steps
        assert steps[2].element_name == "amount_2"

    def test_same_value_all_indices(self):
        """D-05: Every per-index element sent to ActionFactory.run has value == '100'."""
        engine = _make_engine()
        element = _make_indexed_element(
            name="amount_${index}",
            index_range=[0, 3],
            # value is "100" by default in _make_indexed_element
        )
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        captured_elements = []

        def capture_run(el):
            captured_elements.append(el)

        with patch("src.workflow.workflow_engine.DynamicSection"):
            with patch("src.actions.action_factory.ActionFactory.run", side_effect=capture_run):
                engine._run_section(section, ctx)

        assert len(captured_elements) == 4
        for el in captured_elements:
            assert el.value == "100"

    def test_n_results_for_n_indices(self):
        """D-07: range [0, 3] -> len(summary().steps) == 4 (one StepResult per index)."""
        engine = _make_engine()
        element = _make_indexed_element(index_range=[0, 3])
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        _run_section_with_patch(engine, section, ctx, run_side_effect=[None, None, None, None])

        assert len(engine._collector.summary().steps) == 4

    def test_failed_index_does_not_stop_group(self):
        """D-08: A failed index does not abort remaining indices in the group.
        side_effect=[None, ElementActionError('x'), None, None] -> 4 steps,
        exactly one FAILED, three PASSED.
        """
        engine = _make_engine()
        element = _make_indexed_element(index_range=[0, 3])
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        side_effects = [None, ElementActionError("x"), None, None]
        _run_section_with_patch(engine, section, ctx, run_side_effect=side_effects)

        steps = engine._collector.summary().steps
        assert len(steps) == 4
        statuses = [s.status for s in steps]
        assert statuses.count(StepStatus.FAILED) == 1
        assert statuses.count(StepStatus.PASSED) == 3

    def test_missing_index_skipped_when_skip_flag(self):
        """D-09: Element with skip_if_not_visible=True: SkipElementSignal -> SKIPPED, not FAILED."""
        engine = _make_engine()
        element = _make_indexed_element(
            index_range=[0, 2],
            options={"skip_if_not_visible": True},
        )
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        # Index=1 raises SkipElementSignal (not visible on page)
        side_effects = [None, SkipElementSignal("amount_1"), None]
        _run_section_with_patch(engine, section, ctx, run_side_effect=side_effects)

        steps = engine._collector.summary().steps
        assert len(steps) == 3
        statuses = [s.status for s in steps]
        assert statuses[1] == StepStatus.SKIPPED
        assert statuses[0] == StepStatus.PASSED
        assert statuses[2] == StepStatus.PASSED

    def test_missing_index_failed_without_skip_flag(self):
        """D-09b: Without skip flag, ElementActionError -> FAILED; remaining indices still run."""
        engine = _make_engine()
        element = _make_indexed_element(
            index_range=[0, 2],
            # no skip_if_not_visible
        )
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        # Index=1 raises ElementActionError (missing element, no skip tolerance)
        side_effects = [None, ElementActionError("el_1 not found"), None]
        _run_section_with_patch(engine, section, ctx, run_side_effect=side_effects)

        steps = engine._collector.summary().steps
        assert len(steps) == 3
        statuses = [s.status for s in steps]
        assert statuses[1] == StepStatus.FAILED
        assert statuses[0] == StepStatus.PASSED
        assert statuses[2] == StepStatus.PASSED

    def test_embedded_index_in_value(self):
        """WR-03: an embedded ${index} token in element.value is substituted per
        iteration at the engine site (consistent with name/locator handling)."""
        engine = _make_engine()
        element = _make_indexed_element(
            name="amount_${index}",
            index_range=[0, 2],
        )
        # Override value to carry an embedded ${index} token.
        element = element.model_copy(update={"value": "row_${index}_amount"})
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        captured_elements = []

        def capture_run(el):
            captured_elements.append(el)

        with patch("src.workflow.workflow_engine.DynamicSection"):
            with patch("src.actions.action_factory.ActionFactory.run", side_effect=capture_run):
                engine._run_section(section, ctx)

        assert len(captured_elements) == 3
        assert captured_elements[0].value == "row_0_amount"
        assert captured_elements[1].value == "row_1_amount"
        assert captured_elements[2].value == "row_2_amount"

    def test_full_token_value_still_resolves(self):
        """WR-03 no-regression: a full-token value '${index}' still resolves to the
        per-index integer string (the value remains '${index}' at the model level and
        is resolved downstream via merged_params, OR is substituted here — either way
        the action receives the integer string)."""
        engine = _make_engine()
        element = _make_indexed_element(name="amount_${index}", index_range=[0, 2])
        element = element.model_copy(update={"value": "${index}"})
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        captured_elements = []

        def capture_run(el):
            captured_elements.append(el)

        with patch("src.workflow.workflow_engine.DynamicSection"):
            with patch("src.actions.action_factory.ActionFactory.run", side_effect=capture_run):
                engine._run_section(section, ctx)

        assert [el.value for el in captured_elements] == ["0", "1", "2"]

    def test_non_indexed_element_unchanged(self):
        """No-regression: An element with index_range=None produces exactly one step
        under its literal name and one ActionFactory.run call.
        """
        engine = _make_engine()
        element = ElementDefinition(
            name="plain_element",
            type=ElementType.BUTTON,
            action=ActionType.CLICK,
            locator=LocatorDefinition(by="id", value="btn"),
            # No index_range — should behave exactly as before Phase 22
        )
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        mock_run = _run_section_with_patch(engine, section, ctx, run_side_effect=[None])

        assert mock_run.call_count == 1
        steps = engine._collector.summary().steps
        assert len(steps) == 1
        assert steps[0].element_name == "plain_element"

    def test_missing_token_warns_and_runs_n_identical(self, caplog):
        """WR-06: index_range set but no ${index} token in name or locator.value —
        engine logs a WARNING and still runs N iterations, all targeting the same
        concrete name (the deliberately-tolerated author-error path)."""
        import logging

        engine = _make_engine()
        element = _make_indexed_element(
            name="static_amount",
            locator=_make_locator("static_id"),
            index_range=[0, 2],
        )
        section = SectionDefinition(name="Section1", order=1, elements=[element])
        ctx = self._ctx()

        with caplog.at_level(logging.WARNING):
            mock_run = _run_section_with_patch(
                engine, section, ctx, run_side_effect=[None, None, None]
            )

        # N iterations still run despite the missing token.
        assert mock_run.call_count == 3
        # All N StepResults collide on the identical concrete name.
        steps = engine._collector.summary().steps
        assert len(steps) == 3
        assert [s.element_name for s in steps] == ["static_amount"] * 3
        # The warning fired.
        assert any(
            "index_range" in rec.message and "no" in rec.message.lower()
            for rec in caplog.records
            if rec.levelno == logging.WARNING
        )
