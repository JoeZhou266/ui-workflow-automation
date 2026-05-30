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
  - [Dynamic placeholder values](#dynamic-placeholder-values)
  - [Disambiguating checkboxes by name and value](#disambiguating-checkboxes-by-name-and-value)
  - [Skipping invisible optional elements](#skipping-invisible-optional-elements)
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
│       ├── onboarding_workflow.json
│       ├── tabs/               # Reusable tab definitions (referenced via $ref)
│       ├── pages/              # Reusable page definitions (referenced via $ref)
│       └── sections/           # Reusable section definitions (referenced via $ref)
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

### Splitting workflows with `$ref` file references

Large workflows can be split across multiple JSON files. Any object that would inline a tab, page, or section can be replaced with a `$ref` pointer to a standalone JSON file:

```json
{ "$ref": "./relative/path/to/file.json" }
```

The loader resolves `$ref` nodes recursively before validation, so the rest of the framework is unaware of the split. Paths are always relative to the **file that declares them** — not the root workflow file — so nested refs work correctly across subdirectories.

**Example — `sample_workflow.json` (root):**
```json
{
  "workflow_name": "Sample Workflow",
  "start_url": "https://the-internet.herokuapp.com",
  "tabs": [
    { "$ref": "./tabs/form_demo_tab.json" },
    { "$ref": "./tabs/checkboxes_tab.json" },
    { "$ref": "./tabs/dropdown_tab.json" }
  ]
}
```

**Example — `tabs/profile_tab.json` (tab file referencing page files):**
```json
{
  "name": "Profile",
  "order": 1,
  "pages": [
    { "$ref": "../pages/basic_info_page.json" },
    { "$ref": "../pages/employment_info_page.json" }
  ]
}
```

**Rules:**
- A `$ref` object must contain only the `$ref` key — no sibling keys.
- Works at any depth: tabs, pages, sections, or any nested object/list.
- Missing files raise `WorkflowValidationError` with the file path in the message.
- Circular references raise `WorkflowValidationError`.

### Opening and switching browser windows/tabs

Use `switch_to_new_window` or `switch_to_new_tab` to programmatically open a new window or tab and immediately shift WebDriver focus to it. Use `switch_to_latest_window` when a link click or form submission opens a new window asynchronously — the action waits for the new handle to appear, then switches to it. All subsequent elements in the workflow execute inside the new window context.

```json
{
  "name": "Open Report in New Window",
  "type": "button",
  "action": "switch_to_new_window",
  "locator": { "by": "id", "value": "_window" }
}
```

```json
{
  "name": "Switch to Popup Opened by Link Click",
  "type": "button",
  "action": "switch_to_latest_window",
  "locator": { "by": "id", "value": "_window" }
}
```

> **Sentinel locator:** Window-switch actions do not interact with any DOM element. The `locator` field is required by the schema — use `{ "by": "id", "value": "_window" }` as a conventional no-op placeholder. The dispatch layer ignores it.

---

### Executing JavaScript in the browser

Use `execute_js_script` to run arbitrary JavaScript in the browser context. The script string is read from `element.value` and dispatched via `driver.execute_script()` — no DOM element is located or interacted with. The return value is silently discarded.

```json
{
  "name": "Scroll to Bottom",
  "type": "script",
  "action": "execute_js_script",
  "locator": { "by": "id", "value": "_script" },
  "value": "window.scrollTo(0, document.body.scrollHeight);"
}
```

```json
{
  "name": "Remove Overlay",
  "type": "script",
  "action": "execute_js_script",
  "locator": { "by": "id", "value": "_script" },
  "value": "document.getElementById('cookie-banner').remove();"
}
```

> **Sentinel locator:** Script actions do not interact with any DOM element. The `locator` field is required by the schema — use `{ "by": "id", "value": "_script" }` as a conventional no-op placeholder. The dispatch layer ignores it.

> **`value` is required:** If `value` is absent or `null`, the action raises `ElementActionError`. Always provide the JavaScript string.

---

### Dynamic placeholder values

Any `value` field in an `ElementDefinition` that contains a `${token}` pattern is automatically resolved at action-dispatch time — before the value reaches the browser. Only a **full-value token** is expanded; partial matches like `"prefix_${first_name}"` are passed through unchanged.

#### Built-in placeholders

| Token | Returns | Example output |
|---|---|---|
| `${sin_number}` | Random valid Canadian SIN (9 digits, Luhn check). Calls in groups of three return successive 3-digit chunks of the same SIN, then cycle. | `"482013764"` |
| `${first_name}` | Random first name from a built-in list | `"Olivia"` |
| `${last_name}` | Random last name from a built-in list | `"Martinez"` |
| `${random_number}` | Random 7-digit number string | `"3847261"` |
| `${last_day_of_month}` | Last calendar day of the **current month** as `MM/DD/YYYY`. Correctly handles 28/29/30/31-day months including leap-year February. | `"05/31/2026"` |

#### Usage examples

```json
{
  "name": "Date of Service End",
  "type": "text",
  "action": "input",
  "locator": { "by": "id", "value": "end-date" },
  "value": "${last_day_of_month}"
}
```

```json
{
  "name": "First Name",
  "type": "text",
  "action": "input",
  "locator": { "by": "name", "value": "firstName" },
  "value": "${first_name}"
}
```

```json
{
  "name": "SIN Part 1",
  "type": "text",
  "action": "input",
  "locator": { "by": "id", "value": "sin-field-1" },
  "value": "${sin_number}"
}
```

> **Tip — SIN chunking:** `${sin_number}` is designed for forms that split a 9-digit SIN into three separate 3-digit fields. Three consecutive `${sin_number}` elements in the same workflow automatically receive chunks 1, 2, and 3 of the same generated SIN.

> **Unknown tokens raise at runtime:** If `${token}` does not match a registered key, `resolve_dynamic_value()` raises `ValueError` immediately. Check the token spelling against the built-in table above, or register it (see [Extending the Framework](#extending-the-framework)).

---

### Disambiguating checkboxes by name and value

When a form contains multiple `<input type="checkbox">` elements that share the same `name` attribute, use the `value` field to identify the exact checkbox. The framework automatically builds a CSS selector `input[type="checkbox"][name="..."][value="..."]` — no manual CSS required. This mirrors the existing behaviour for `select_radio`.

This is opt-in and fully backwards-compatible: if `value` is absent or `locator.by` is not `name`, the plain locator is used unchanged.

**Check a specific checkbox by name and value:**
```json
{
  "name": "Select Sports Hobby",
  "type": "checkbox",
  "action": "check",
  "locator": { "by": "name", "value": "hobby" },
  "value": "sports"
}
```

**Uncheck a specific checkbox:**
```json
{
  "name": "Deselect Cooking Hobby",
  "type": "checkbox",
  "action": "uncheck",
  "locator": { "by": "name", "value": "hobby" },
  "value": "cooking"
}
```

Both actions are idempotent — `check` does nothing if the checkbox is already checked, and `uncheck` does nothing if it is already unchecked.

**How the locator is resolved:**

| `locator.by` | `value` field | Locator used |
|---|---|---|
| `name` | `"sports"` | `input[type="checkbox"][name="hobby"][value="sports"]` (CSS selector) |
| `name` | absent / `""` | `By.NAME, "hobby"` (plain locator, same as before) |
| `id`, `css_selector`, etc. | any | plain locator, `value` ignored for location |

---

### Skipping invisible optional elements

Set `options.skip_if_not_visible: true` on any element to make it conditional. Before running `pre_wait` or the action, the engine probes element visibility. If the element is not present or not visible, the step is recorded as **SKIPPED** (not FAILED) and execution continues to the next element.

This is the correct approach for UI elements that are conditionally rendered — for example, a cookie banner, a promotional modal, or a progress indicator that only appears on certain runs.

```json
{
  "name": "Cookie Banner Accept",
  "type": "button",
  "action": "click",
  "locator": { "by": "css_selector", "value": "#cookie-accept-btn" },
  "options": { "skip_if_not_visible": true }
}
```

```json
{
  "name": "Dismiss Promo Modal",
  "type": "button",
  "action": "click",
  "locator": { "by": "id", "value": "promo-close" },
  "options": { "skip_if_not_visible": true },
  "post_wait": {
    "condition": "invisible",
    "locator": { "by": "id", "value": "promo-modal" },
    "timeout": 5
  }
}
```

**Behaviour summary:**

| Element visible? | `skip_if_not_visible` set? | Outcome |
|---|---|---|
| Yes | `true` | Runs normally (pre_wait → action → post_wait) |
| No | `true` | Recorded as **SKIPPED**, execution continues |
| Yes or No | absent / `false` | Standard behaviour — not visible causes `WaitTimeoutError` |

> **`pre_wait` is never called for skipped elements.** The visibility probe runs first, so no wait cost is incurred when an optional element is absent.

> **SKIPPED ≠ FAILED.** Skipped steps are counted in `ExecutionSummary.skipped`, not `failed`. `passed_rate` is calculated from `passed / total`, so skipped steps do not reduce the pass rate.

---

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
| `value` | any | | Input value, option text, file path, JavaScript string (for `execute_js_script`), etc. |
| `required` | boolean | | If `true` and `value` is absent, validation fails |
| `pre_wait` | object | | `WaitConditionDefinition` — wait before interaction |
| `post_wait` | object | | `WaitConditionDefinition` — wait after interaction |
| `assertions` | array | | Post-action `AssertionDefinition` checks |
| `retryable` | boolean | | Retry on failure |
| `retry_count` | integer | | Number of retries (max 10) |
| `options` | object | | Extra per-action options. Supported keys: `skip_if_not_visible: true` (see [Skipping invisible optional elements](#skipping-invisible-optional-elements)), `trigger_change_event: true` |

#### LoadCriteria / WaitConditionDefinition

| Field | Type | Default | Description |
|---|---|---|---|
| `condition` | string | `visible` | Wait condition type (see [Wait Conditions](#wait-condition-types)) |
| `locator` | object | | Target element locator |
| `timeout` | integer | `20` / `10` | Max seconds to wait. For `wait_seconds`, reused as the sleep duration (1–300 s). |
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

`text` · `textarea` · `number` · `email` · `button` · `checkbox` · `radio` · `select` · `multiselect` · `date` · `link` · `label` · `file` · `script`

### Action Types

| Action | Description |
|---|---|
| `input` | Clear field and type text (also handles `number` and `email` inputs) |
| `click` | Smart click (scroll into view, wait for clickable, retry on intercept) |
| `select_by_text` | Select a `<select>` option by visible text |
| `select_by_value` | Select a `<select>` option by `value` attribute |
| `select_by_index` | Select a `<select>` option by zero-based index |
| `check` | Check a checkbox if not already checked. When `locator.by` is `name` and `value` is set, builds a targeted CSS selector to locate the exact checkbox — see [Disambiguating checkboxes by name and value](#disambiguating-checkboxes-by-name-and-value). |
| `uncheck` | Uncheck a checkbox if currently checked. Supports the same name+value disambiguation as `check`. |
| `select_radio` | Select a radio button if not already selected. When `locator.by` is `name` and `value` is set, builds `input[type="radio"][name="..."][value="..."]` to locate the exact button. |
| `upload` | Set a file path on a file input element |
| `switch_to_new_window` | Open a new browser window and switch focus to it |
| `switch_to_new_tab` | Open a new browser tab and switch focus to it |
| `switch_to_latest_window` | Wait for a new window/tab to appear (e.g. opened by a link click) and switch focus to it |
| `execute_js_script` | Execute an arbitrary JavaScript string (from `value`) in the browser. No DOM element is resolved. Raises `ElementActionError` if `value` is absent. Return value is silently discarded. |
| `assert_only` | Run assertions without performing an interaction |
| `noop` | Skip this element entirely |

### Locator Strategies

`id` · `name` · `class_name` · `css_selector` · `xpath` · `link_text` · `partial_link_text` · `tag_name`

---

## Synchronisation and Wait Strategies

The framework is designed for AJAX-heavy applications. All waits are explicit — `time.sleep()` is never used as an ad-hoc synchronisation strategy. The sole exception is the `wait_seconds` condition, which provides a sanctioned, isolated, and logged fixed-duration pause for the rare case where a deterministic event cannot be detected.

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
| `wait_seconds` | Fixed-duration pause — sleeps for `timeout` seconds unconditionally. No locator required. Use as a last resort when a deterministic event cannot be detected. |

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

**Pause for 3 seconds after triggering an async background job (no detectable DOM event):**
```json
{
  "name": "Trigger Export",
  "type": "button",
  "action": "click",
  "locator": { "by": "id", "value": "exportButton" },
  "post_wait": {
    "condition": "wait_seconds",
    "timeout": 3
  }
}
```

> **Note:** `wait_seconds` is a last resort. Prefer event-driven conditions (`visible`, `ajax_idle`, `text_contains`, etc.) whenever the application provides a detectable signal. A WARNING-level log line is emitted each time `wait_seconds` fires, making intentional pauses visible in logs.

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
        │     ├── [visibility probe]          (skip_if_not_visible → raises SkipElementSignal)
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

### Add a custom placeholder token

Add a zero-argument generator function and register it in `PLACEHOLDER_REGISTRY` inside `src/actions/value_resolver.py`. No other files need to change — `ValueResolver` and `resolve_dynamic_value()` pick up the new token automatically.

```python
# src/actions/value_resolver.py

def generate_today_iso() -> str:
    """Return today's date as YYYY-MM-DD."""
    from datetime import date
    return date.today().isoformat()

PLACEHOLDER_REGISTRY: Dict[str, Callable[[], str]] = {
    ...
    "today_iso": generate_today_iso,   # add here
}
```

Usage in workflow JSON:

```json
{ "value": "${today_iso}" }
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
