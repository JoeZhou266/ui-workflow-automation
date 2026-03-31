# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project goal

Data-driven Selenium workflow automation framework in **Python 3.9.13**. Reads workflow definitions from JSON files and executes browser interactions across a hierarchy of: Workflow → Tabs → Pages → Sections → Elements.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run a single test file
pytest tests/test_workflow_runner.py -v

# Run smoke tests only
pytest tests/smoke/ -v

# Run unit tests only (no browser)
pytest tests/unit/ -v

# Run with a specific workflow JSON
pytest tests/smoke/test_sample_workflow.py --workflow testdata/workflows/sample_workflow.json

# Run headless
pytest --headless

# Run with environment config
pytest --env qa
```

## Stack

- **Python 3.9.13** — use `from __future__ import annotations` for forward refs
- **selenium** — browser automation
- **pytest** — test runner with fixtures for driver lifecycle
- **pydantic v1 or v2** — JSON schema validation (check installed version before using v2 syntax)
- **PyYAML** — environment config files
- **python-dotenv** — local env vars

## Architecture

The framework uses a hybrid model: Page Objects for page navigation/readiness, Section Components for reusable UI areas, and a metadata-driven action engine for element interactions. JSON is runtime configuration — no hardcoded Python class per workflow.

### Layer responsibilities

| Layer | Location | Responsibility |
|---|---|---|
| Models | `src/models/` | Pydantic types for workflow JSON (`WorkflowDefinition`, `TabDefinition`, `PageDefinition`, `SectionDefinition`, `ElementDefinition`) |
| Data | `src/data/` | JSON loading and validation |
| Driver | `src/driver/` | Chrome/Edge/Firefox factory, headless/headed, teardown |
| Locators | `src/locators/` | Maps JSON `by` strings → Selenium `By` values |
| UI base | `src/ui/` | `BasePage` and `BaseComponent` with all Selenium interaction methods |
| Actions | `src/actions/` | Dispatches element actions based on `element.type` + `element.action` |
| Waits | `src/waits/` | Centralized wait layer (see below) |
| Workflow | `src/workflow/` | Orchestrates hierarchy traversal, result collection, screenshots |
| Core | `src/core/` | Config, constants, exceptions, logger, enums |

### Synchronization layer (`src/waits/`)

This is critical — the application under test is AJAX-heavy. All waits go through this layer:

- `wait_manager.py` — single entry point wrapping `WebDriverWait`, logs what it waits for, raises typed timeout errors
- `expected_states.py` — custom `ExpectedCondition` implementations (text_equals, options_count_greater_than, spinner_gone, overlay_gone, etc.)
- `ajax_monitor.py` — JS-based readiness checks (`document.readyState`, jQuery idle if present); must fail gracefully if globals absent
- `page_readiness.py` — combines document ready + load_criteria + spinner/overlay absence

Never use `time.sleep()` as a synchronization strategy. Any fallback sleep must be isolated in one helper, configurable, logged at WARNING, and commented with the reason.

### Workflow execution sequence

```
load JSON → validate → open start_url
  for each tab (sorted by order):
    for each page (sorted by order):
      wait_for_page_ready(load_criteria)
      for each section (sorted by order):
        for each element (in order):
          execute pre_wait
          execute action
          execute post_wait
          record StepResult
```

On any failure: capture screenshot + page HTML, record phase (page_load / pre_wait / action / post_wait), continue or abort per config.

### Domain model key fields

**ElementDefinition** adds: `pre_wait`, `post_wait`, `retryable`, `retry_count`

**LoadCriteria** includes: `locator`, `condition`, `timeout`, `require_document_ready`, `require_ajax_idle`, `spinner_locator`, `overlay_locator`

**WaitConditionType** values: `visible`, `clickable`, `present`, `invisible`, `selected`, `url_contains`, `text_equals`, `text_contains`, `value_equals`, `attribute_contains`, `attribute_equals`, `count_greater_than`, `options_count_greater_than`, `document_ready`, `ajax_idle`, `spinner_gone`, `overlay_gone`, `enabled`

### Locator `by` values supported

`id`, `name`, `class_name`, `css_selector`, `xpath`, `link_text`, `partial_link_text`, `tag_name`

## Key constraints

- Prefer `id`, `name`, `data-*`, or stable CSS selectors over XPath
- Re-locate elements rather than caching `WebElement` references across AJAX re-renders; handle `StaleElementReferenceException` in wait/action helpers
- `safe_click()`: wait visible → scroll into view → wait clickable → click → optional post_wait
- `clear_and_type()`: wait visible+enabled → clear → type → optional blur/tab for change events
- Implicit wait must stay at 0; use explicit waits exclusively
- Environment config (base URLs, credentials) must come from `configs/env.*.yaml` or `.env`, never hardcoded

## Test organization

```
tests/
  conftest.py          # driver fixture, config fixture, workflow fixture
  unit/                # no browser: JSON parsing, validation, locator resolution, action dispatch
  smoke/               # real browser flows against sample workflows
```

Pytest fixtures own the driver lifecycle (`scope="function"` by default). The `--env`, `--headless`, and `--workflow` options are registered in `conftest.py`.