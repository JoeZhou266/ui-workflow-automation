# UI Workflow Automation Framework

A data-driven Selenium test automation framework in Python 3.9.13. Workflows are defined entirely in JSON — no Python code changes are needed to add new test scenarios. The framework reads a workflow file, validates it, opens a browser, and executes a hierarchy of tabs → pages → sections → elements with full AJAX synchronisation support.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Writing Workflow JSON](#writing-workflow-json)
- [Supported Element Types and Actions](#supported-element-types-and-actions)
- [Synchronisation and Wait Strategies](#synchronisation-and-wait-strategies)
- [Running Tests](#running-tests)
- [Architecture Overview](#architecture-overview)
- [Execution Result Model](#execution-result-model)
- [Extending the Framework](#extending-the-framework)

---

## Requirements

| Dependency | Version |
|---|---|
| Python | 3.9.13 |
| Google Chrome | Latest stable |
| selenium | ≥ 4.15 |
| pydantic | ≥ 2.0 |
| pytest | ≥ 7.4 |
| PyYAML | ≥ 6.0 |
| python-dotenv | ≥ 1.0 |
| webdriver-manager | ≥ 4.0 |

---

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd ui-workflow-automation

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example environment file
cp .env.example .env
# Edit .env to set BASE_URL and any overrides for your environment
```

> **Note on ChromeDriver:** `webdriver-manager` automatically downloads the correct ChromeDriver binary for your installed Chrome version. If you are in a locked-down environment, set `driver_path` manually or place the binary on `PATH`.

---

## Project Structure

```
ui-workflow-automation/
├── configs/                    # Per-environment YAML config files
│   ├── env.dev.yaml
│   ├── env.qa.yaml
│   └── env.prod.yaml
├── reports/                    # Test output (screenshots, HTML reports)
├── src/
│   ├── actions/                # Action dispatch layer (element_actions, action_factory, value_resolver)
│   ├── core/                   # Enums, exceptions, constants, logger, config
│   ├── data/                   # JSON loader and semantic validator
│   ├── driver/                 # WebDriver factory and lifecycle manager
│   ├── locators/               # Locator resolver (JSON → Selenium By)
│   ├── models/                 # Pydantic domain models (workflow, element, result)
│   ├── ui/                     # BasePage, BaseComponent, DynamicPage, DynamicSection
│   ├── utils/                  # File helpers, string utilities, screenshot manager
│   ├── waits/                  # Centralised wait layer (wait_manager, expected_states, ajax_monitor, page_readiness)
│   └── workflow/               # Orchestration engine (workflow_engine, navigator, result_collector, execution_context)
├── testdata/
│   └── workflows/              # Workflow JSON files
│       ├── sample_workflow.json
│       └── onboarding_workflow.json
├── tests/
│   ├── conftest.py             # Pytest fixtures and CLI options
│   ├── unit/                   # Unit tests (no browser)
│   └── smoke/                  # End-to-end tests (real browser)
├── .env.example
├── pytest.ini
├── pyproject.toml
└── requirements.txt
```

---

## Quick Start

```bash
# Run unit tests (no browser required)
pytest tests/unit/ -v

# Run the sample smoke workflow against the-internet.herokuapp.com
pytest tests/smoke/ \
  --workflow testdata/workflows/sample_workflow.json \
  --headless -v

# Run against QA environment
pytest tests/smoke/ \
  --workflow testdata/workflows/sample_workflow.json \
  --env qa -v
```

---

## Configuration

Configuration is resolved in priority order: **environment variable → YAML file → built-in default**.

### Environment YAML files

Place environment-specific settings in `configs/env.<name>.yaml`:

```yaml
# configs/env.dev.yaml
base_url: "http://localhost:3000"
browser: chrome
headless: false
implicit_wait: 0
page_load_timeout: 30
explicit_wait_timeout: 10
ajax_idle_timeout: 15
poll_frequency_ms: 500
screenshots_dir: reports/screenshots
log_level: DEBUG
window_width: 1920
window_height: 1080
# driver_path:          # e.g. /usr/local/bin/chromedriver  (leave commented to use webdriver-manager)
# browser_binary_path:  # e.g. /opt/google/chrome/chrome    (leave commented to use system default)
```

`driver_path` points to the **WebDriver binary** (chromedriver, geckodriver, msedgedriver). When set, `webdriver-manager` is bypassed entirely. When absent, `webdriver-manager` auto-downloads the matching driver.

`browser_binary_path` points to the **browser executable** itself (useful for non-default installs such as Chrome Canary, a pinned corporate build, or a CI-managed binary). When absent, Selenium uses the browser found on `PATH`.

### Environment variables (`.env` or shell)

| Variable | Default | Description |
|---|---|---|
| `BASE_URL` | _(from YAML)_ | Override base URL for all navigation |
| `BROWSER` | `chrome` | `chrome`, `firefox`, or `edge` |
| `HEADLESS` | `false` | `true` to suppress browser window |
| `PAGE_LOAD_TIMEOUT` | `30` | Seconds before page load times out |
| `EXPLICIT_WAIT_TIMEOUT` | `10` | Default explicit wait timeout |
| `AJAX_IDLE_TIMEOUT` | `15` | Timeout for jQuery/AJAX idle checks |
| `SCREENSHOTS_DIR` | `reports/screenshots` | Output directory for failure screenshots |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `DRIVER_PATH` | _(auto via webdriver-manager)_ | Absolute path to the WebDriver binary (chromedriver / geckodriver / msedgedriver) |
| `BROWSER_BINARY_PATH` | _(system default)_ | Absolute path to the browser executable (Chrome, Firefox, Edge) |

### Pytest CLI options

| Option | Description |
|---|---|
| `--env <name>` | Load `configs/env.<name>.yaml` (default: `dev`) |
| `--headless` | Run headless regardless of YAML setting |
| `--browser <name>` | Override browser (`chrome`, `firefox`, `edge`) |
| `--workflow <path>` | Path to workflow JSON for smoke tests |

---

## Writing Workflow JSON

A workflow file describes the full test execution tree. The engine iterates everything in `order` sequence.

### Minimal example

```json
{
  "workflow_name": "My Workflow",
  "start_url": "https://example.com/app",
  "tabs": [
    {
      "name": "Registration",
      "order": 1,
      "pages": [
        {
          "name": "Sign Up Form",
          "order": 1,
          "load_criteria": {
            "condition": "visible",
            "locator": { "by": "id", "value": "signup-form" },
            "timeout": 15,
            "require_document_ready": true
          },
          "sections": [
            {
              "name": "User Details",
              "order": 1,
              "elements": [
                {
                  "name": "Email",
                  "type": "text",
                  "action": "input",
                  "locator": { "by": "name", "value": "email" },
                  "value": "user@example.com",
                  "required": true
                },
                {
                  "name": "Submit",
                  "type": "button",
                  "action": "click",
                  "locator": { "by": "css_selector", "value": "button[type='submit']" },
                  "post_wait": {
                    "condition": "visible",
                    "locator": { "by": "css_selector", "value": ".success-message" },
                    "timeout": 10
                  }
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### Full field reference

#### WorkflowDefinition (root)

| Field | Type | Required | Description |
|---|---|---|---|
| `workflow_name` | string | ✓ | Display name for the workflow |
| `description` | string | | Optional description |
| `start_url` | string | ✓ | URL opened before traversal begins |
| `tabs` | array | | List of `TabDefinition` |
| `metadata` | object | | Arbitrary key/value metadata |

#### TabDefinition

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Tab label |
| `order` | integer | | Execution sequence (default: 1) |
| `pages` | array | | List of `PageDefinition` |

#### PageDefinition

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Page label |
| `order` | integer | | Execution sequence (default: 1) |
| `path` | string | | Optional path appended to `base_url` for direct navigation |
| `load_criteria` | object | | See `LoadCriteria` — defines when the page is ready |
| `sections` | array | | List of `SectionDefinition` |

#### SectionDefinition

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Section label |
| `order` | integer | | Execution sequence (default: 1) |
| `locator` | object | | Optional root locator — scopes element searches to a container |
| `repeatable` | boolean | | Reserved for future repeating-section support |
| `elements` | array | | List of `ElementDefinition` |

#### ElementDefinition

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Element label (must be unique within a section) |
| `type` | string | ✓ | See [Element Types](#element-types) |
| `action` | string | ✓ | See [Action Types](#action-types) |
| `locator` | object | ✓ | `{ "by": "<strategy>", "value": "<selector>" }` |
| `value` | any | | Input value, option text, file path, etc. |
| `required` | boolean | | If `true` and `value` is absent, validation fails |
| `pre_wait` | object | | `WaitConditionDefinition` — wait before interaction |
| `post_wait` | object | | `WaitConditionDefinition` — wait after interaction |
| `assertions` | array | | Post-action `AssertionDefinition` checks |
| `retryable` | boolean | | Retry on failure |
| `retry_count` | integer | | Number of retries (max 10) |
| `options` | object | | Extra per-action options (e.g. `trigger_change_event: true`) |

#### LoadCriteria / WaitConditionDefinition

| Field | Type | Default | Description |
|---|---|---|---|
| `condition` | string | `visible` | Wait condition type (see [Wait Conditions](#wait-condition-types)) |
| `locator` | object | | Target element locator |
| `timeout` | integer | `20` / `10` | Max seconds to wait |
| `poll_frequency_ms` | integer | `500` | How often to check the condition |
| `require_document_ready` | boolean | `true` | Wait for `document.readyState == complete` |
| `require_ajax_idle` | boolean | `false` | Wait for jQuery AJAX requests to finish |
| `spinner_locator` | object | | Wait for this element to disappear before checking condition |
| `overlay_locator` | object | | Wait for this overlay to disappear |
| `text_expected` | string | | Expected text for `text_equals` / `text_contains` / `url_contains` |
| `attribute_name` | string | | Attribute name for `attribute_equals` / `attribute_contains` |
| `attribute_value` | string | | Expected attribute value |
| `minimum_count` | integer | | Minimum count for `count_greater_than` / `options_count_greater_than` |

---

## Supported Element Types and Actions

### Element Types

`text` · `textarea` · `button` · `checkbox` · `radio` · `select` · `multiselect` · `date` · `link` · `label` · `file`

### Action Types

| Action | Description |
|---|---|
| `input` | Clear field and type text |
| `click` | Smart click (scroll into view, wait for clickable, retry on intercept) |
| `select_by_text` | Select a `<select>` option by visible text |
| `select_by_value` | Select a `<select>` option by `value` attribute |
| `select_by_index` | Select a `<select>` option by zero-based index |
| `check` | Check a checkbox if not already checked |
| `uncheck` | Uncheck a checkbox if currently checked |
| `upload` | Set a file path on a file input element |
| `assert_only` | Run assertions without performing an interaction |
| `noop` | Skip this element entirely |

### Locator Strategies

`id` · `name` · `class_name` · `css_selector` · `xpath` · `link_text` · `partial_link_text` · `tag_name`

---

## Synchronisation and Wait Strategies

The framework is designed for AJAX-heavy applications. All waits are explicit — `time.sleep()` is never used as a synchronisation strategy.

### Wait priority order

1. **Page readiness** — `load_criteria` evaluated before any section/element interaction
2. **Element `pre_wait`** — runs immediately before the action
3. **Element action** — the actual browser interaction
4. **Element `post_wait`** — runs immediately after the action
5. **Assertions** — optional verification step after post_wait

### Wait Condition Types

| Condition | Description |
|---|---|
| `visible` | Element is present and visible |
| `clickable` | Element is visible and enabled |
| `present` | Element exists in DOM |
| `invisible` | Element is hidden or absent |
| `selected` | Checkbox / radio is selected |
| `url_contains` | Current URL contains `text_expected` |
| `text_equals` | Element text exactly matches `text_expected` |
| `text_contains` | Element text contains `text_expected` |
| `value_equals` | Element `value` attribute equals `text_expected` |
| `attribute_equals` | Attribute `attribute_name` equals `attribute_value` |
| `attribute_contains` | Attribute `attribute_name` contains `attribute_value` |
| `count_greater_than` | Number of matching elements exceeds `minimum_count` |
| `options_count_greater_than` | `<select>` has more than `minimum_count` options |
| `document_ready` | `document.readyState === 'complete'` |
| `ajax_idle` | document ready AND jQuery has no active AJAX requests |
| `spinner_gone` | Spinner element is invisible |
| `overlay_gone` | Overlay element is invisible |
| `enabled` | Element is visible and enabled |

### AJAX pattern examples

**Wait for a cascading dropdown to populate after a country selection:**
```json
{
  "name": "Province",
  "type": "select",
  "action": "select_by_text",
  "locator": { "by": "id", "value": "province" },
  "value": "Ontario",
  "pre_wait": {
    "condition": "options_count_greater_than",
    "locator": { "by": "id", "value": "province" },
    "minimum_count": 1,
    "timeout": 15,
    "require_ajax_idle": true
  }
}
```

**Click Save and wait for success toast while spinner clears:**
```json
{
  "name": "Save",
  "type": "button",
  "action": "click",
  "locator": { "by": "id", "value": "saveButton" },
  "post_wait": {
    "condition": "text_contains",
    "locator": { "by": "css_selector", "value": ".toast-message" },
    "text_expected": "saved successfully",
    "timeout": 20,
    "spinner_locator": { "by": "css_selector", "value": ".loading-mask" }
  }
}
```

---

## Running Tests

```bash
# All unit tests (no browser)
pytest tests/unit/ -v

# Single unit test file
pytest tests/unit/test_workflow_models.py -v

# Single test by name
pytest tests/unit/test_json_loader.py::TestWorkflowLoader::test_load_valid_file -v

# Smoke test with a specific workflow
pytest tests/smoke/ \
  --workflow testdata/workflows/sample_workflow.json \
  --env dev --headless -v

# Smoke test with Firefox
pytest tests/smoke/ \
  --workflow testdata/workflows/sample_workflow.json \
  --browser firefox --headless -v

# Run with a locally installed ChromeDriver (bypasses webdriver-manager)
DRIVER_PATH=/usr/local/bin/chromedriver \
pytest tests/smoke/ \
  --workflow testdata/workflows/sample_workflow.json \
  --env dev -v

# Run with a non-default Chrome binary (e.g. Chrome Canary or a pinned CI build)
BROWSER_BINARY_PATH="/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" \
pytest tests/smoke/ \
  --workflow testdata/workflows/sample_workflow.json \
  --env dev --headless -v

# Combine both — local driver AND specific browser binary
DRIVER_PATH=/usr/local/bin/chromedriver \
BROWSER_BINARY_PATH=/opt/chrome-stable/chrome \
pytest tests/smoke/ \
  --workflow testdata/workflows/sample_workflow.json \
  --env dev --headless -v

# Run only tests matching a marker
pytest -m unit -v
pytest -m smoke -v

# With HTML report
pytest tests/unit/ --html=reports/unit-report.html -v
```

---

## Architecture Overview

```
WorkflowEngine
  │
  ├── WorkflowLoader + WorkflowValidator    (validate JSON before execution)
  ├── Navigator                             (URL navigation)
  ├── ResultCollector                       (accumulates StepResult records)
  │
  └── For each Tab → Page → Section → Element:
        │
        ├── PageReadinessChecker            (load_criteria + spinner/overlay/AJAX)
        ├── ActionFactory
        │     ├── WaitManager.wait_for_condition(pre_wait)
        │     ├── ElementActions.execute()
        │     │     └── BasePage / BaseComponent interaction methods
        │     └── WaitManager.wait_for_condition(post_wait)
        └── ResultCollector.record_pass/fail/skip
```

### Layer map

| Layer | Package | Responsibility |
|---|---|---|
| Domain models | `src/models/` | Pydantic types; validates JSON structure at parse time |
| Data I/O | `src/data/` | File loading, JSON parsing, semantic validation |
| Driver | `src/driver/` | Browser creation and lifecycle (Chrome / Firefox / Edge) |
| Locators | `src/locators/` | Translates `{ by, value }` JSON to `(selenium.By, str)` |
| Waits | `src/waits/` | All explicit waits: `WaitManager`, custom `ExpectedCondition` implementations, `AjaxMonitor`, `PageReadinessChecker` |
| UI | `src/ui/` | `BasePage` and `BaseComponent` — all Selenium interaction primitives |
| Actions | `src/actions/` | `ElementActions` (per-action dispatch), `ActionFactory` (pre/post wait lifecycle), `ValueResolver` (variable substitution hook) |
| Workflow | `src/workflow/` | `WorkflowEngine` (traversal), `Navigator` (URL routing), `ResultCollector` (step results), `ExecutionContext` (location tracking) |
| Utils | `src/utils/` | File helpers, string utilities, screenshot capture |
| Core | `src/core/` | Enums, typed exceptions, constants, structured logger, `AppConfig` |

---

## Execution Result Model

`WorkflowEngine.run()` returns an `ExecutionSummary`:

```python
@dataclass
class ExecutionSummary:
    workflow_name: str
    total: int
    passed: int
    failed: int
    skipped: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    passed_rate: float        # 0.0–100.0
    steps: list[StepResult]

@dataclass
class StepResult:
    workflow_name: str
    tab_name: str
    page_name: str
    section_name: str
    element_name: str
    action: ActionType
    status: StepStatus        # passed | failed | skipped
    timestamp: datetime
    duration_ms: float
    error_message: str        # populated on failure
    failure_phase: FailurePhase  # page_load_wait | pre_action_wait | interaction | post_action_wait | assertion
    screenshot_path: str      # path to PNG on failure
```

On failure the engine automatically:
1. Captures a timestamped screenshot to `screenshots_dir`
2. Records the `failure_phase` so you know whether the failure was during page load, pre-wait, the interaction itself, or post-wait
3. Continues executing remaining elements (fail-and-continue behaviour)

---

## Extending the Framework

### Add variable substitution to values

Edit `src/actions/value_resolver.py`:

```python
def _resolve_string(self, value: str) -> str:
    from datetime import date
    return value.replace("${today}", date.today().isoformat())
```

### Add a custom wait condition

Add a callable to `src/waits/expected_states.py` and handle the new `WaitConditionType` enum value in the `_dispatch` method of `WaitManager`.

### Add a custom element action

1. Add a value to `ActionType` in `src/core/enums.py`
2. Add a branch in `ElementActions.execute()` in `src/actions/element_actions.py`

### Use the engine programmatically

```python
from src.core.config import AppConfig
from src.data.json_loader import WorkflowLoader
from src.data.validators import WorkflowValidator
from src.driver.driver_manager import DriverManager
from src.workflow.workflow_engine import WorkflowEngine

config = AppConfig(env="qa")
definition = WorkflowLoader.load("testdata/workflows/sample_workflow.json")
WorkflowValidator().validate_or_raise(definition)

with DriverManager(config) as driver:
    engine = WorkflowEngine(
        driver=driver,
        definition=definition,
        base_url=config.base_url,
        default_wait_timeout=config.explicit_wait_timeout,
        screenshots_dir=config.screenshots_dir,
    )
    summary = engine.run()
    print(f"Passed: {summary.passed}/{summary.total}")
```
