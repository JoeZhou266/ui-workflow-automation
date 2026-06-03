# UI Workflow Automation Framework

A data-driven Selenium browser automation framework for Python 3.14. Define browser workflows entirely in JSON — no Python code changes required to add new test scenarios. The framework reads a workflow file, validates it, opens a browser, and executes a hierarchy of Tabs → Pages → Sections → Elements with full AJAX synchronisation support.

![Python](https://img.shields.io/badge/python-3.14.5-blue)
![Selenium](https://img.shields.io/badge/selenium-%E2%89%A54.15-brightgreen)
![Pydantic](https://img.shields.io/badge/pydantic-v2-orange)
![pytest](https://img.shields.io/badge/pytest-%E2%89%A57.4-blueviolet)
![Tests](https://img.shields.io/badge/unit_tests-394_passing-success)
![Coverage](https://img.shields.io/badge/coverage-reports%2Fcoverage%2F-informational)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Environment YAML files](#environment-yaml-files)
  - [Environment variables (.env or shell)](#environment-variables-env-or-shell)
  - [Pytest CLI options](#pytest-cli-options)
- [Workflow JSON Configuration](#workflow-json-configuration)
  - [Minimal example](#minimal-example)
  - [Splitting workflows with $ref file references](#splitting-workflows-with-ref-file-references)
  - [Workflow parameters and conditional $ref](#workflow-parameters-and-conditional-ref)
  - [Opening and switching browser windows/tabs](#opening-and-switching-browser-windowstabs)
  - [Executing JavaScript in the browser](#executing-javascript-in-the-browser)
  - [Dynamic placeholder values](#dynamic-placeholder-values)
  - [Workflow parameter values in elements](#workflow-parameter-values-in-elements)
  - [${env:KEY} config placeholders](#envkey-config-placeholders)
  - [Disambiguating checkboxes by name and value](#disambiguating-checkboxes-by-name-and-value)
  - [Skipping invisible optional elements](#skipping-invisible-optional-elements)
  - [Full field reference](#full-field-reference)
- [Supported Element Types and Actions](#supported-element-types-and-actions)
- [Synchronisation and Wait Strategies](#synchronisation-and-wait-strategies)
- [Usage](#usage)
- [Programmatic API](#programmatic-api)
- [Execution Result Model](#execution-result-model)
- [Test Video Capture](#test-video-capture)
- [Test Coverage Reports](#test-coverage-reports)
- [Project Structure](#project-structure)
- [Extending the Framework](#extending-the-framework)

---

## Overview

**Problem:** Automating repetitive browser workflows traditionally requires writing Python (or similar) code for every new scenario — page objects, test classes, locator constants. Each new workflow means new code, reviews, and deployments.

**Solution:** This framework inverts that model. Browser workflows are declared as JSON files that describe what to do. The framework reads those files and does it. Adding a new workflow means writing a JSON file, not Python.

### Key capabilities

#### 🗂 Workflow Authoring
| Feature | Description |
|---|---|
| **Zero Python per workflow** | Define tabs, pages, sections, and element interactions entirely in JSON — no code changes to add new scenarios |
| **Composable with `$ref`** | Split large workflows across multiple files; reference shared tabs, pages, or sections by relative path |
| **Parameters & conditional branches** | Declare named parameters at the workflow root and include/exclude tabs or pages using `condition` expressions with `==`, `!=`, `&&`, and `\|\|` operators |
| **Parameter value expansion** | Use `${param_name}` in any element `value` field to inject a workflow parameter at action-dispatch time |
| **Dynamic placeholders** | Built-in tokens for random names, SIN numbers, dates, and env config values; extensible via a registry |

#### 🌐 Browser Control
| Feature | Description |
|---|---|
| **Multi-browser** | Chrome (default), Firefox, and Edge; headless or headed |
| **AJAX-aware synchronisation** | Every wait is explicit — `WaitManager` wraps `WebDriverWait` with 19 condition types including jQuery idle, spinner/overlay removal, and attribute/text assertions |
| **Conditional element skip** | Mark any element `skip_if_not_visible: true` to record it as SKIPPED rather than FAILED when absent from the DOM |
| **JavaScript execution** | Run arbitrary browser JS as a first-class action type |

#### 📊 Observability & Reporting
| Feature | Description |
|---|---|
| **Structured results** | Every step returns a typed `StepResult` with status, duration, failure phase, and screenshot path |
| **HTML test report** | Auto-generated timestamped report after every `pytest` run — per-test step drill-downs, color-coded rows, and video links for failed tests |
| **Test coverage reports** | pytest-cov runs automatically; produces a standard report at `reports/coverage/index.html` and a per-package branch drilldown at `reports/coverage/custom_index.html` |
| **Test video capture** | Record browser sessions as `.mp4` via ffmpeg — retained on failure, discarded on pass |
| **Daily-rolling log file** | Opt-in file logging via `LOG_FILE_PATH`; rotates at midnight, retains 30 days; stdout logging always active |

---

## Architecture

### Component overview

```
WorkflowEngine
  │
  ├── WorkflowLoader           Load + $ref-resolve + parameter expansion
  ├── WorkflowValidator        Semantic checks after parse
  ├── Navigator                URL navigation (start_url, page.path)
  ├── ResultCollector          Accumulates StepResult records
  │
  └── For each Tab → Page → Section → Element:
        │
        ├── DynamicPage / PageReadinessChecker   load_criteria + spinner/overlay/AJAX
        ├── ActionFactory
        │     ├── [visibility probe]             skip_if_not_visible → SkipElementSignal
        │     ├── WaitManager.wait_for_condition(pre_wait)
        │     ├── ElementActions.execute()
        │     │     └── BasePage / DynamicSection interaction methods
        │     └── WaitManager.wait_for_condition(post_wait)
        └── ResultCollector.record_pass/fail/skip
```

### Layer map

| Layer | Package | Responsibility |
|---|---|---|
| Domain models | `src/models/` | Pydantic types; validates JSON structure at parse time |
| Data I/O | `src/data/` | File loading, `$ref` resolution, parameter expansion, semantic validation |
| Driver | `src/driver/` | Browser creation and lifecycle (Chrome / Firefox / Edge) |
| Locators | `src/locators/` | Translates `{ by, value }` JSON to `(selenium.By, str)` |
| Waits | `src/waits/` | All explicit waits: `WaitManager`, custom `ExpectedCondition` implementations, `AjaxMonitor`, `PageReadinessChecker` |
| UI | `src/ui/` | `BasePage` and `BaseComponent` — all Selenium interaction primitives |
| Actions | `src/actions/` | `ElementActions` (per-action dispatch), `ActionFactory` (lifecycle), `ValueResolver` (placeholder expansion) |
| Workflow | `src/workflow/` | `WorkflowEngine` (traversal), `Navigator`, `ResultCollector`, `ExecutionContext` |
| Utils | `src/utils/` | File helpers, string utilities, screenshot capture |
| Core | `src/core/` | Enums, typed exceptions, constants, structured logger, `AppConfig` |

### Key design decisions

| Decision | Outcome |
|----------|---------|
| `$ref` is full-replacement — no sibling key merging | Simpler, unambiguous; `condition` is the only carve-out |
| Circular `$ref` guard uses `frozenset` | Immutable, hashable, correct for recursive calls |
| Placeholder regex is anchored full-value-only | No partial substitution — `"prefix_${sin}"` passes through unchanged |
| `WaitConditionDefinition.timeout` reused for `wait_seconds` | No schema change for fixed-duration pause |
| JS execution is value-only (no element binding) | Simpler; return value silently discarded |
| `env:` namespace routes to `_ENV_CONFIG` before `PLACEHOLDER_REGISTRY` | Clear precedence, no key collision risk |
| Workflow parameters are load-time only | Keeps runtime engine unchanged; conditional branches resolved before Pydantic validation |
| Implicit wait stays at 0 | Explicit-only wait strategy; no race between implicit and explicit timeouts |

---

## Prerequisites

| Requirement | Version / Notes |
|---|---|
| Python | 3.14.5 |
| Google Chrome | Latest stable — or provide `driver_path` / `browser_binary_path` for a specific version |
| ChromeDriver | Auto-managed by `webdriver-manager`, or supply manually via `DRIVER_PATH` |
| Firefox | Optional — required only when `--browser firefox` |
| Microsoft Edge | Optional — required only when `--browser edge` |
| ffmpeg | Optional — required only when `record_video: true`; skipped silently when absent |

No cloud service or database is required. The framework runs entirely locally against a target web application.

---

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd ui-workflow-automation

# 2. Create and activate a virtual environment
python3.14 -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example environment file and configure it
cp .env.example .env
# Edit .env to set BASE_URL and any overrides
```

> **ChromeDriver note:** `webdriver-manager` automatically downloads the correct ChromeDriver binary for your installed Chrome version on first run. In locked-down environments, set `DRIVER_PATH` to the chromedriver binary path to bypass this.

### ffmpeg (optional — required for video recording only)

Install ffmpeg if you plan to use `record_video: true`. The framework runs fine without it — recording is silently skipped when ffmpeg is absent.

```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu / Debian
sudo apt update && sudo apt install -y ffmpeg

# Windows (Chocolatey)
choco install ffmpeg

# Windows (Scoop)
scoop install ffmpeg

# Windows (winget)
winget install --id Gyan.FFmpeg
```

> **Windows PATH note:** After installing, open a new terminal and verify with `ffmpeg -version`. Chocolatey and Scoop add ffmpeg to `PATH` automatically; for a manual install, add the `bin/` folder to your system `PATH` environment variable.

---

## Configuration

Configuration is resolved in priority order: **environment variable → YAML file → built-in default**.

### Environment YAML files

Place environment-specific settings in `configs/env.<name>.yaml`. The `--env` flag selects which file to load (default: `dev`).

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
record_video: false       # set to true to capture .mp4 for smoke tests (requires ffmpeg, skipped in headless)
videos_dir: reports/videos
# driver_path:          # e.g. /usr/local/bin/chromedriver  (leave commented to use webdriver-manager)
# browser_binary_path:  # e.g. /opt/google/chrome/chrome    (leave commented to use system default)
# log_file_path:        # e.g. logs/workflow.log             (leave commented to disable file logging)
```

Every top-level key in the YAML file is also accessible from workflow JSON via `${env:KEY}` — see [`${env:KEY}` config placeholders](#envkey-config-placeholders).

`driver_path` points to the **WebDriver binary** (chromedriver, geckodriver, msedgedriver). When set, `webdriver-manager` is bypassed entirely.

`browser_binary_path` points to the **browser executable** (useful for Chrome Canary, a pinned corporate build, or a CI-managed binary). When absent, Selenium uses the browser on `PATH`.

### Environment variables (.env or shell)

| Variable | Default | Description |
|---|---|---|
| `BASE_URL` | _(from YAML)_ | Override base URL for all navigation |
| `BROWSER` | `chrome` | `chrome`, `firefox`, or `edge` |
| `HEADLESS` | `false` | `true` to suppress the browser window |
| `IMPLICIT_WAIT` | `0` | Keep at 0 — the framework uses explicit waits exclusively |
| `PAGE_LOAD_TIMEOUT` | `30` | Seconds before page load times out |
| `EXPLICIT_WAIT_TIMEOUT` | `10` | Default explicit wait timeout in seconds |
| `AJAX_IDLE_TIMEOUT` | `15` | Timeout for jQuery/AJAX idle checks |
| `POLL_FREQUENCY_MS` | `500` | How often wait conditions are polled (ms) |
| `SCREENSHOTS_DIR` | `reports/screenshots` | Output directory for failure screenshots |
| `RECORD_VIDEO` | `false` | `true` to enable ffmpeg screen recording for smoke tests |
| `VIDEOS_DIR` | `reports/videos` | Output directory for failure videos |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `DRIVER_PATH` | _(auto via webdriver-manager)_ | Absolute path to the WebDriver binary |
| `BROWSER_BINARY_PATH` | _(system default)_ | Absolute path to the browser executable |
| `LOG_FILE_PATH` | _(disabled)_ | Path for the daily-rolling log file (e.g. `logs/workflow.log`). When set, a `TimedRotatingFileHandler` is added alongside stdout. Rotates at midnight, retains 30 days. Parent directory is auto-created. |

### Pytest CLI options

| Option | Description |
|---|---|
| `--env <name>` | Load `configs/env.<name>.yaml` (default: `dev`) |
| `--headless` | Run headless regardless of YAML setting |
| `--browser <name>` | Override browser (`chrome`, `firefox`, `edge`) |
| `--workflow <path>` | Path to workflow JSON for smoke tests |

---

## Workflow JSON Configuration

A workflow file describes the full browser execution tree. The engine iterates everything in `order` sequence.

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

---

### Splitting workflows with $ref file references

Large workflows can be split across multiple JSON files. Any tab, page, or section object can be replaced with a `$ref` pointer to a standalone JSON file:

```json
{ "$ref": "./relative/path/to/file.json" }
```

The loader resolves `$ref` nodes **recursively before validation**. Paths are always relative to the file that declares them — so nested refs work correctly across subdirectories.

**Root workflow referencing tab files:**

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

**Tab file referencing page files:**

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
- A `$ref` object may only contain `$ref` (and optionally `condition` — see below). All other sibling keys are ignored.
- Works at any depth: tabs, pages, sections, or any nested object or list.
- Missing files raise `WorkflowValidationError` with the file path in the message.
- Circular references raise `WorkflowValidationError`.

---

### Workflow parameters and conditional $ref

#### Overview

`WorkflowDefinition` supports a `parameters` block — a flat list of named string values declared at the workflow root. Parameters let a single workflow JSON file define multiple structural variants (different tabs, pages, or sections) selected **at load time** based on parameter values. This avoids duplicating entire workflow files when only part of the structure changes between scenarios.

**Common use cases:**
- Different account types each requiring a different onboarding tab sequence
- Feature-flagged pages that only apply in certain environments
- Optional sections that are skipped for a specific product tier
- Environment-specific tabs driven by YAML config values

Parameters are resolved once when the file is loaded, before Pydantic validation, before the browser opens. The engine never sees excluded nodes — they simply do not exist in the validated model.

#### Declaring parameters

Add a `parameters` list to the workflow root. Each entry is an object with `name` and `value` keys. Values are always strings. Multiple parameters are allowed.

```json
{
  "workflow_name": "Customer Onboarding",
  "start_url": "https://example.com/app",
  "parameters": [
    { "name": "account_type", "value": "OPEN" },
    { "name": "kyc_required", "value": "true" }
  ],
  "tabs": [...]
}
```

#### Condition syntax

Attach a `condition` key as a sibling of `$ref` on any tab, page, or section reference. When the condition evaluates to `false`, the node is silently omitted from its parent list.

**Simple condition (single atom):**

```
"condition": "${<param_name>} <operator> '<value>'"
```

| Operator | Meaning | Example condition |
|---|---|---|
| `==` | Parameter equals value | `"${account_type} == 'OPEN'"` |
| `!=` | Parameter does not equal value | `"${account_type} != 'PREMIUM'"` |

**Compound conditions (`&&` / `||`):**

Multiple atoms can be combined with `&&` (AND) and `||` (OR). `&&` binds tighter than `||`.

```
"condition": "${param1} == 'A' && ${param2} == 'B'"
"condition": "${param1} == 'A' || ${param2} == 'B'"
"condition": "${param1} == 'A' && ${param2} == 'B' || ${param3} == 'C'"
```

The third example evaluates as `(param1 == 'A' AND param2 == 'B') OR param3 == 'C'`.

| Operator | Binding | Meaning |
|---|---|---|
| `&&` | higher precedence | Both atoms must be true |
| `\|\|` | lower precedence | Either atom must be true |

**Rules:**
- `${param_name}` must match a name declared in `parameters`. An undefined name raises `WorkflowValidationError` at load time.
- The right-hand side value must be wrapped in **single quotes**: `'value'`.
- All comparisons are **string equality** — no type coercion, no numeric comparison.
- In compound conditions, **all atoms are evaluated before combining** — an undefined parameter in any atom raises `WorkflowValidationError` regardless of where it appears, even in a position that logical short-circuit would normally skip.
- Extra whitespace around `&&` and `||` is tolerated.
- Parentheses are not supported — use `&&`-before-`||` precedence instead.
- A `$ref` node without a `condition` key resolves unconditionally, same as before.
- `condition` is the only sibling key on a `$ref` node that is evaluated. All other sibling keys are ignored.

#### Example — branching tabs by account type

```json
{
  "workflow_name": "Customer Onboarding",
  "start_url": "https://example.com/app",
  "parameters": [
    { "name": "account_type", "value": "OPEN" }
  ],
  "tabs": [
    { "$ref": "./tabs/registration_tab.json" },
    {
      "$ref": "./tabs/open_account_tab.json",
      "condition": "${account_type} == 'OPEN'"
    },
    {
      "$ref": "./tabs/managed_account_tab.json",
      "condition": "${account_type} == 'MANAGED'"
    },
    {
      "$ref": "./tabs/non_premium_tab.json",
      "condition": "${account_type} != 'PREMIUM'"
    },
    { "$ref": "./tabs/confirmation_tab.json" }
  ]
}
```

With `account_type = "OPEN"`:
- `registration_tab.json` — included (no condition)
- `open_account_tab.json` — **included** (`"OPEN" == 'OPEN'` → true)
- `managed_account_tab.json` — **omitted** (`"OPEN" == 'MANAGED'` → false)
- `non_premium_tab.json` — **included** (`"OPEN" != 'PREMIUM'` → true)
- `confirmation_tab.json` — included (no condition)

#### Example — conditional pages within a tab

Conditions work at any depth. A tab file can apply conditions to its own page references:

```json
{
  "name": "KYC Verification",
  "order": 2,
  "pages": [
    { "$ref": "../pages/id_upload_page.json" },
    {
      "$ref": "../pages/enhanced_kyc_page.json",
      "condition": "${kyc_required} == 'true'"
    },
    {
      "$ref": "../pages/standard_summary_page.json",
      "condition": "${kyc_required} != 'true'"
    }
  ]
}
```

And a page file can apply conditions to its own section references:

```json
{
  "name": "Account Details",
  "order": 1,
  "sections": [
    { "$ref": "../sections/basic_info.json" },
    {
      "$ref": "../sections/business_info.json",
      "condition": "${account_type} == 'BUSINESS'"
    }
  ]
}
```

#### Example — compound condition on a single $ref node

Use `&&` when a tab or page should only be included if multiple conditions are all true:

```json
{
  "workflow_name": "Onboarding",
  "start_url": "https://example.com/app",
  "parameters": [
    { "name": "account_type", "value": "OPEN" },
    { "name": "kyc_required", "value": "false" }
  ],
  "tabs": [
    { "$ref": "./tabs/registration_tab.json" },
    {
      "$ref": "./tabs/summary_tab.json",
      "condition": "${account_type} == 'OPEN' && ${kyc_required} == 'false'"
    },
    {
      "$ref": "./tabs/kyc_tab.json",
      "condition": "${account_type} == 'OPEN' && ${kyc_required} == 'true'"
    },
    { "$ref": "./tabs/confirmation_tab.json" }
  ]
}
```

With `account_type = "OPEN"` and `kyc_required = "false"`:
- `summary_tab.json` — **included** (both atoms true)
- `kyc_tab.json` — **omitted** (second atom false: `"false" == 'true'` → false)

Use `||` when a tab should be included if *any* condition is true:

```json
{
  "$ref": "./tabs/premium_or_managed_tab.json",
  "condition": "${account_type} == 'PREMIUM' || ${account_type} == 'MANAGED'"
}
```

#### Example — multiple parameters

Multiple parameters can be declared and referenced independently across different `$ref` nodes in the same workflow:

```json
{
  "workflow_name": "Onboarding v2",
  "start_url": "https://example.com/app",
  "parameters": [
    { "name": "account_type", "value": "OPEN" },
    { "name": "kyc_required", "value": "true" },
    { "name": "region",       "value": "CA" }
  ],
  "tabs": [
    { "$ref": "./tabs/registration_tab.json" },
    {
      "$ref": "./tabs/kyc_tab.json",
      "condition": "${kyc_required} == 'true'"
    },
    {
      "$ref": "./tabs/canada_compliance_tab.json",
      "condition": "${region} == 'CA'"
    },
    {
      "$ref": "./tabs/managed_tab.json",
      "condition": "${account_type} == 'MANAGED'"
    }
  ]
}
```

Each `$ref` node evaluates its own condition independently. Compound `&&` / `||` logic operates within a single condition string — there is no implicit AND/OR between conditions on separate nodes.

#### Driving parameters from environment config

Parameter values may contain `${env:KEY}` tokens, resolved against the active YAML file at load time. This lets environment config drive the structural variant without changing the workflow JSON:

```json
{
  "workflow_name": "Onboarding",
  "start_url": "https://example.com/app",
  "parameters": [
    { "name": "account_type", "value": "${env:default_account_type}" },
    { "name": "kyc_required", "value": "${env:kyc_required}" }
  ],
  "tabs": [
    { "$ref": "./tabs/registration_tab.json" },
    {
      "$ref": "./tabs/kyc_tab.json",
      "condition": "${kyc_required} == 'true'"
    }
  ]
}
```

```yaml
# configs/env.qa.yaml
default_account_type: "OPEN"
kyc_required: "true"

# configs/env.prod.yaml
default_account_type: "MANAGED"
kyc_required: "false"
```

Running with `--env qa` includes the KYC tab. Running with `--env prod` excludes it. The workflow JSON file is identical in both cases.

#### Load-time resolution sequence

```
WorkflowLoader.load(path)
  │
  ├─ 1. Parse raw JSON
  ├─ 2. Extract parameters[] from root
  ├─ 3. Resolve ${env:KEY} in each parameter value → params dict
  ├─ 4. resolve_refs(data, params=params)
  │       ├─ For each $ref node:
  │       │     ├─ Read condition sibling key (if present)
  │       │     ├─ evaluate_condition(condition, params)
  │       │     │     Supports simple atoms (${p} == 'v') and compound
  │       │     │     conditions joined by && / || (&&-before-|| precedence)
  │       │     │     true  → load and resolve the referenced file recursively
  │       │     │     false → return None (omitted from parent list)
  │       │     └─ No condition → load unconditionally
  │       └─ Filter None values out of all parent lists
  └─ 5. WorkflowDefinition.model_validate(resolved_data)
```

#### Error behaviour

| Scenario | Outcome |
|---|---|
| `condition` references a name not in `parameters` | `WorkflowValidationError` at load time — fail fast |
| `condition` evaluates to `false` | `$ref` node silently omitted from parent list |
| `condition` evaluates to `true` | Referenced file is loaded and resolved recursively |
| `$ref` node has no `condition` | Resolves unconditionally (same as before) |
| Compound condition has an undefined param in any atom | `WorkflowValidationError` — all atoms are evaluated before combining, so undefined params are never silently skipped by short-circuit |
| Compound condition has a malformed atom (e.g. `bad_atom`) | `WorkflowValidationError: Malformed condition atom` |
| Parameter `value` contains invalid `${env:KEY}` | `WorkflowValidationError` — YAML key not found |

> **Scope:** `parameters` is declared at the workflow root only. Tabs, pages, and sections inherit the parameters read-only — there are no per-level parameter blocks and no parameter override rules.

> **Conditional $ref at element level is not supported.** Use `options.skip_if_not_visible: true` (see [Skipping invisible optional elements](#skipping-invisible-optional-elements)) for runtime conditional element execution.

---

### Opening and switching browser windows/tabs

| Action | Behaviour |
|---|---|
| `switch_to_new_window` | Opens a new browser window and switches WebDriver focus to it |
| `switch_to_new_tab` | Opens a new browser tab and switches WebDriver focus to it |
| `switch_to_latest_window` | Waits for any new window/tab handle to appear (e.g. opened by a link click), then switches to it |

All subsequent elements in the workflow execute inside the new window context.

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

Use `execute_js_script` to run arbitrary JavaScript. The script string is read from `element.value` and dispatched via `driver.execute_script()`. No DOM element is located or interacted with. The return value is silently discarded.

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
  "name": "Remove Cookie Banner",
  "type": "script",
  "action": "execute_js_script",
  "locator": { "by": "id", "value": "_script" },
  "value": "document.getElementById('cookie-banner').remove();"
}
```

> **Sentinel locator:** Use `{ "by": "id", "value": "_script" }` as a conventional placeholder. The dispatch layer ignores it for `execute_js_script` actions.

> **`value` is required.** If `value` is absent or `null`, the action raises `ElementActionError`.

---

### Dynamic placeholder values

Any `value` field in an `ElementDefinition` that is a `${token}` pattern is automatically resolved at action-dispatch time. Only a **full-value token** (the entire string is the token) is expanded — partial patterns like `"prefix_${first_name}"` are passed through unchanged.

#### Built-in placeholders

| Token | Returns | Example output |
|---|---|---|
| `${sin_number}` | Successive 3-digit chunks of a random valid Canadian SIN (Luhn check). Three consecutive calls return chunks 1, 2, and 3 of the same SIN. | `"482"`, `"013"`, `"764"` |
| `${first_name}` | Random first name from a built-in list | `"Olivia"` |
| `${last_name}` | Random last name from a built-in list | `"Martinez"` |
| `${random_number}` | Random 7-digit number string | `"3847261"` |
| `${last_day_of_next_month}` | Last calendar day of next month as `MM/DD/YYYY`. Correctly handles 28/29/30/31-day months including leap-year February and December→January year-wrap. | `"06/30/2026"` (called in May 2026) |

#### Usage examples

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
  "name": "Service End Date",
  "type": "text",
  "action": "input",
  "locator": { "by": "id", "value": "end-date" },
  "value": "${last_day_of_next_month}"
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

> **SIN chunking:** Three consecutive `${sin_number}` elements automatically receive chunks 1, 2, and 3 of the same 9-digit SIN — designed for forms that split a SIN into three separate 3-digit fields.

> **Unknown tokens raise at runtime.** If `${token}` does not match a registered key, `resolve_dynamic_value()` raises `ValueError`. Check the token spelling against the built-in table, or register it (see [Extending the Framework](#extending-the-framework)).

---

### Workflow parameter values in elements

Parameters declared in the workflow `parameters` block can be used as `${param_name}` tokens in any element `value` field. Resolution happens at action-dispatch time — the same mechanism as built-in placeholders — so parameter values flow through the same expansion path without requiring any changes to the element or action code.

```json
{
  "workflow_name": "Onboarding",
  "start_url": "https://example.com/app",
  "parameters": [
    { "name": "account_type", "value": "OPEN" },
    { "name": "applicant_name", "value": "Jane Smith" }
  ],
  "tabs": [
    {
      "name": "Application",
      "order": 1,
      "pages": [
        {
          "name": "Details",
          "order": 1,
          "sections": [
            {
              "name": "Applicant",
              "order": 1,
              "elements": [
                {
                  "name": "Full Name",
                  "type": "text",
                  "action": "input",
                  "locator": { "by": "id", "value": "applicant-name" },
                  "value": "${applicant_name}"
                },
                {
                  "name": "Account Type",
                  "type": "text",
                  "action": "input",
                  "locator": { "by": "id", "value": "account-type" },
                  "value": "${account_type}"
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

`${applicant_name}` resolves to `"Jane Smith"` and `${account_type}` resolves to `"OPEN"` at the moment each element is dispatched. Parameters override built-in tokens of the same name — declare unique names to avoid collisions.

> **Scope:** Only parameters declared in the workflow `parameters` block are available as `${param_name}` tokens in element values. Parameters from parent workflows (via `$ref`) are not inherited.

---

### ${env:KEY} config placeholders

Use `${env:KEY}` to inject a value directly from the active environment YAML file into a workflow. This keeps environment-specific data — account numbers, credentials, base paths — in `configs/env.<name>.yaml` rather than hardcoded in workflow JSON.

**How it works:** `AppConfig` calls `configure_env_resolver()` during initialisation, populating a module-level dict from the loaded YAML. At action-dispatch time, any `value` field matching `${env:KEY}` looks up `KEY` in that dict and substitutes the result.

```json
{
  "name": "Account Number",
  "type": "text",
  "action": "input",
  "locator": { "by": "id", "value": "accountNumber" },
  "value": "${env:account_number}"
}
```

The corresponding YAML must define the key at the top level:

```yaml
# configs/env.qa.yaml
base_url: "https://qa.example.com"
account_number: "ACC-001"
login_password: "s3cr3t!"
```

**Error behaviour:**

| Scenario | Outcome |
|---|---|
| Key exists in YAML | Returns the value as a string |
| Key not in YAML | `ValueError: Unknown env config key 'KEY'. Available keys: [...]` |
| YAML file is empty | `ValueError` for any `${env:...}` token |

> **Shell env vars are not read.** `${env:KEY}` resolves only against the YAML file. It does not read `os.environ` or `.env` overrides.

> **Coexistence with built-in placeholders.** `${env:KEY}` and built-in tokens like `${sin_number}` can appear in the same workflow without conflict — the `env:` prefix routes to the YAML dict while bare tokens route to `PLACEHOLDER_REGISTRY`.

---

### Disambiguating checkboxes by name and value

When a form contains multiple `<input type="checkbox">` elements sharing the same `name` attribute, set `value` in the element definition to identify the exact checkbox. The framework automatically builds a CSS selector `input[type="checkbox"][name="..."][value="..."]` — no manual CSS required.

```json
{
  "name": "Select Sports Hobby",
  "type": "checkbox",
  "action": "check",
  "locator": { "by": "name", "value": "hobby" },
  "value": "sports"
}
```

```json
{
  "name": "Deselect Cooking Hobby",
  "type": "checkbox",
  "action": "uncheck",
  "locator": { "by": "name", "value": "hobby" },
  "value": "cooking"
}
```

Both actions are idempotent — `check` does nothing if already checked, `uncheck` does nothing if already unchecked.

| `locator.by` | `value` field | Locator used |
|---|---|---|
| `name` | `"sports"` | `input[type="checkbox"][name="hobby"][value="sports"]` (CSS selector) |
| `name` | absent / `""` | `By.NAME, "hobby"` (plain locator, unchanged) |
| `id`, `css_selector`, etc. | any | plain locator, `value` ignored for location |

The same name+value disambiguation applies to `select_radio` using `input[type="radio"][name="..."][value="..."]`.

---

### Skipping invisible optional elements

Set `options.skip_if_not_visible: true` on any element to make it conditional. Before running `pre_wait` or the action, the engine probes visibility. If the element is absent or hidden, the step is recorded as **SKIPPED** (not FAILED) and execution continues.

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

| Element visible? | `skip_if_not_visible` set? | Outcome |
|---|---|---|
| Yes | `true` | Runs normally (pre_wait → action → post_wait) |
| No | `true` | Recorded as **SKIPPED**, execution continues |
| Yes or No | absent / `false` | Standard — not visible causes `WaitTimeoutError` |

> **`pre_wait` is never called for skipped elements.** The visibility probe runs first, so no wait cost is incurred when an optional element is absent.

> **SKIPPED ≠ FAILED.** Skipped steps count in `ExecutionSummary.skipped`, not `failed`. `passed_rate` is calculated from `passed / total`, so skipped steps do not reduce the pass rate.

---

### Full field reference

#### WorkflowDefinition (root)

| Field | Type | Required | Description |
|---|---|---|---|
| `workflow_name` | string | ✓ | Display name for the workflow |
| `description` | string | | Optional description |
| `start_url` | string | ✓ | URL opened before traversal begins |
| `tabs` | array | | List of `TabDefinition` (or `$ref` nodes) |
| `parameters` | array | | List of `ParameterDefinition` — `{ "name": str, "value": str }` |
| `metadata` | object | | Arbitrary key/value metadata |

#### ParameterDefinition

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Parameter name — referenced in conditions as `${name}` |
| `value` | string | ✓ | Parameter value; may contain `${env:KEY}` tokens resolved at load time |

#### TabDefinition

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Tab label |
| `order` | integer | | Execution sequence (default: 1) |
| `pages` | array | | List of `PageDefinition` (or `$ref` nodes) |

#### PageDefinition

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Page label |
| `order` | integer | | Execution sequence (default: 1) |
| `path` | string | | Optional path appended to `base_url` for direct navigation |
| `load_criteria` | object | | `LoadCriteria` — defines when the page is ready |
| `sections` | array | | List of `SectionDefinition` (or `$ref` nodes) |

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
| `value` | any | | Input value, option text, file path, or JavaScript string (for `execute_js_script`) |
| `required` | boolean | | If `true` and `value` is absent, validation fails |
| `pre_wait` | object | | `WaitConditionDefinition` — wait before interaction |
| `post_wait` | object | | `WaitConditionDefinition` — wait after interaction |
| `assertions` | array | | Post-action `AssertionDefinition` checks |
| `retryable` | boolean | | Retry on failure |
| `retry_count` | integer | | Number of retries (max 10) |
| `options` | object | | Extra per-action options. Supported keys: `skip_if_not_visible: true`, `trigger_change_event: true` |

#### LoadCriteria / WaitConditionDefinition

| Field | Type | Default | Description |
|---|---|---|---|
| `condition` | string | `visible` | Wait condition type — see [Wait Condition Types](#wait-condition-types) |
| `locator` | object | | Target element locator |
| `timeout` | integer | `20` / `10` | Max seconds to wait. For `wait_seconds`, reused as the sleep duration (1–300 s). |
| `poll_frequency_ms` | integer | `500` | How often to check the condition |
| `require_document_ready` | boolean | `true` | Wait for `document.readyState == complete` |
| `require_ajax_idle` | boolean | `false` | Wait for jQuery AJAX requests to finish |
| `spinner_locator` | object | | Wait for this spinner element to disappear before checking condition |
| `overlay_locator` | object | | Wait for this overlay element to disappear |
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
| `click` | Smart click — scroll into view, wait for clickable, retry on intercept |
| `select_by_text` | Select a `<select>` option by visible text |
| `select_by_value` | Select a `<select>` option by `value` attribute |
| `select_by_index` | Select a `<select>` option by zero-based index |
| `check` | Check a checkbox if not already checked. When `locator.by` is `name` and `value` is set, builds a targeted CSS selector. |
| `uncheck` | Uncheck a checkbox if currently checked. Supports the same name+value disambiguation as `check`. |
| `select_radio` | Select a radio button if not already selected. When `locator.by` is `name` and `value` is set, builds `input[type="radio"][name="..."][value="..."]`. |
| `upload` | Set a file path on a file input element |
| `switch_to_new_window` | Open a new browser window and switch focus to it |
| `switch_to_new_tab` | Open a new browser tab and switch focus to it |
| `switch_to_latest_window` | Wait for a new window/tab to appear (e.g. opened by a link click) and switch focus |
| `execute_js_script` | Execute an arbitrary JavaScript string (from `value`) in the browser. Return value is silently discarded. Raises `ElementActionError` if `value` is absent. |
| `assert_only` | Run assertions without performing an interaction |
| `noop` | Skip this element entirely |

### Locator Strategies

`id` · `name` · `class_name` · `css_selector` · `xpath` · `link_text` · `partial_link_text` · `tag_name`

---

## Synchronisation and Wait Strategies

The framework is designed for AJAX-heavy applications. All waits are explicit — `time.sleep()` is never used as an ad-hoc synchronisation strategy. The sole exception is the `wait_seconds` condition, which provides a sanctioned, logged, fixed-duration pause for the rare case where a deterministic event cannot be detected.

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
| `enabled` | Element is visible and enabled |
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
| `wait_seconds` | Fixed-duration pause — sleeps for `timeout` seconds unconditionally. No locator required. Use as a last resort when a deterministic event cannot be detected. Emits a WARNING log line each time it fires. |

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

> **Note:** `wait_seconds` is a last resort. Prefer event-driven conditions (`visible`, `ajax_idle`, `text_contains`, etc.) whenever the application provides a detectable signal.

---

## Usage

```bash
# Run all unit tests (no browser required)
pytest tests/unit/ -v

# Run a single unit test file
pytest tests/unit/test_workflow_models.py -v

# Run a single test by name
pytest tests/unit/test_json_loader.py::TestWorkflowLoader::test_load_valid_file -v

# Run smoke tests against the dev environment (headless)
pytest tests/smoke/ \
  --workflow testdata/workflows/sample_workflow.json \
  --env dev --headless -v

# Run smoke tests against QA
pytest tests/smoke/ \
  --workflow testdata/workflows/sample_workflow.json \
  --env qa -v

# Run smoke tests with Firefox
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

# HTML report is auto-generated on every run — open reports/run_report_<timestamp>.html
pytest tests/unit/ -v

# Run with coverage (default — pytest.ini wires --cov automatically)
pytest tests/unit/ -v
# Opens: reports/coverage/index.html        — standard per-file coverage
#        reports/coverage/custom_index.html — branch drilldown grouped by package

# Run without coverage (faster — skips .coverage data collection)
pytest tests/unit/ -v --no-cov

# View the coverage reports
open reports/coverage/index.html          # macOS — standard coverage report
open reports/coverage/custom_index.html   # macOS — per-file branch drilldown
# Windows: start reports\coverage\index.html
```

---

## Programmatic API

Use the engine directly from Python without pytest, for integration into other automation pipelines or scripts.

```python
from src.core.config import AppConfig
from src.data.json_loader import WorkflowLoader
from src.data.validators import WorkflowValidator
from src.driver.driver_manager import DriverManager
from src.workflow.workflow_engine import WorkflowEngine

# Load configuration from configs/env.qa.yaml (merged with env vars / .env)
config = AppConfig(env="qa")

# Load and $ref-resolve the workflow JSON, then validate
definition = WorkflowLoader.load("testdata/workflows/sample_workflow.json")
WorkflowValidator().validate_or_raise(definition)

# Run the workflow — DriverManager handles browser lifecycle
with DriverManager(config) as driver:
    engine = WorkflowEngine(
        driver=driver,
        definition=definition,
        base_url=config.base_url,
        default_wait_timeout=config.explicit_wait_timeout,
        screenshots_dir=config.screenshots_dir,
    )
    summary = engine.run()

print(f"Passed: {summary.passed}/{summary.total} ({summary.passed_rate:.1f}%)")
print(f"Failed: {summary.failed}  Skipped: {summary.skipped}")
print(f"Duration: {summary.duration_seconds:.2f}s")

# Inspect individual step results
for step in summary.steps:
    if step.status.value == "failed":
        print(f"FAILED: {step.location}")
        print(f"  Phase: {step.failure_phase}")
        print(f"  Error: {step.error_message}")
        print(f"  Screenshot: {step.screenshot_path}")
```

---

## Execution Result Model

`WorkflowEngine.run()` returns an `ExecutionSummary`:

```python
class ExecutionSummary(BaseModel):
    workflow_name: str
    total: int
    passed: int
    failed: int
    skipped: int
    start_time: datetime
    end_time: datetime
    steps: list[StepResult]

    @property
    def duration_seconds(self) -> float: ...

    @property
    def passed_rate(self) -> float: ...      # 0.0–100.0

class StepResult(BaseModel):
    workflow_name: str
    tab_name: str
    page_name: str
    section_name: str
    element_name: str
    action: ActionType
    status: StepStatus          # passed | failed | skipped
    timestamp: datetime
    duration_ms: float
    error_message: str          # populated on failure
    failure_phase: FailurePhase # page_load_wait | pre_action_wait | interaction | post_action_wait | assertion
    screenshot_path: str        # path to PNG on failure
```

On failure the engine automatically:
1. Captures a timestamped PNG to `screenshots_dir`
2. Records `failure_phase` so you know whether the failure occurred during page load, pre-wait, the interaction itself, or post-wait
3. Continues executing remaining elements (fail-and-continue behaviour)

---

## Test Video Capture

The `video_recorder` fixture records the browser session as an H.264 `.mp4` file using ffmpeg. On pass the video is deleted. On failure it is retained in `reports/videos/` alongside the failure screenshot.

### Prerequisites

ffmpeg must be on `PATH`. See [ffmpeg installation](#ffmpeg-optional--required-for-video-recording-only) in the Installation section for platform-specific commands.

If ffmpeg is absent, `VideoManager` logs a `WARNING` and silently skips recording — no test fails because of a missing ffmpeg binary.

### Enabling recording

Set `record_video: true` in the active environment YAML:

```yaml
# configs/env.dev.yaml
record_video: true
videos_dir: reports/videos   # optional — this is the default
```

Or override at runtime via environment variable:

```bash
RECORD_VIDEO=true pytest tests/smoke/ --workflow testdata/workflows/sample_workflow.json --env dev -v
```

### Headless mode

Recording is automatically skipped when `--headless` is active. ffmpeg captures the physical display; there is no virtual display (Xvfb) dependency. CI headless runs produce no video — use headed mode (e.g. with Xvfb in Linux CI) to retain failure videos.

### Using the fixture in a smoke test

Request `video_recorder` alongside `driver` in any smoke test. The fixture handles start, retain-or-delete, and the video path automatically:

```python
def test_registration_workflow(driver, app_config, workflow_definition, video_recorder):
    engine = WorkflowEngine(
        driver=driver,
        definition=workflow_definition,
        base_url=app_config.base_url,
        default_wait_timeout=app_config.explicit_wait_timeout,
        screenshots_dir=app_config.screenshots_dir,
    )
    summary = engine.run()
    assert summary.failed == 0
```

`video_recorder` yields the video file path (or `None` when recording is unavailable). On test failure the path is stashed in `pytest`'s item stash so the HTML report can link to it automatically.

### Output

Retained videos are written to `reports/videos/` with the naming pattern `YYYYMMDD_HHMMSS_<safe_test_name>.mp4`. The file name mirrors the `ScreenshotManager` convention.

| Outcome | Video file |
|---------|-----------|
| Test passes | Deleted immediately after teardown |
| Test fails | Retained at `reports/videos/<timestamp>_<name>.mp4` |
| Headless run | No file created (silently skipped) |
| ffmpeg absent | No file created (WARNING logged) |
| `record_video: false` | No file created |

---

## Test Coverage Reports

Coverage is collected automatically on every `pytest` run via `pytest.ini`. No extra flags are needed.

### What gets generated

| File | Description |
|------|-------------|
| `reports/coverage/index.html` | Standard coverage.py per-file HTML report — statement and branch counts, highlighted source |
| `reports/coverage/custom_index.html` | Custom per-package drilldown — branch columns (Branch / BrPart), package grouping, direct links to per-file pages |
| `reports/coverage/src_*.html` | Per-file annotated source — red lines (missed), yellow lines (partial branch) |

Both HTML files are generated after every successful test run. The `custom_index.html` is written by a `pytest_sessionfinish` hook (`tests/conftest.py`) that reads the `.coverage` binary produced by pytest-cov.

### Skipping coverage

Pass `--no-cov` to skip data collection entirely — useful when iterating quickly on a single file:

```bash
pytest tests/unit/test_coverage_index.py -v --no-cov
```

The `pytest_sessionfinish` hook automatically detects `--no-cov` and skips writing `custom_index.html`.

### Branch coverage

`.coveragerc` enables branch coverage tracking:

```ini
[run]
source = src
branch = true
```

The `Branch` and `BrPart` columns in `custom_index.html` show which decision points were fully exercised:

- **Branch** — total number of branch points in the file
- **BrPart** — branches taken in only one direction (partial coverage, highlighted yellow in per-file view)

### Report structure

```
reports/
├── coverage/
│   ├── index.html             # Standard coverage.py entry point
│   ├── custom_index.html      # Per-package branch drilldown (auto-generated)
│   ├── style_cb_*.css         # coverage.py stylesheet
│   └── src_*.html             # Per-file annotated source pages
└── run_report_<timestamp>.html  # HTML test report — links to coverage from each test row
```

The HTML test report (`run_report_*.html`) includes a **Coverage Report** link in each test row's extras section when `reports/coverage/index.html` exists, so you can jump directly from a failing test to the coverage view.

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
│   ├── actions/                # Action dispatch — element_actions, action_factory, value_resolver
│   ├── core/                   # Enums, exceptions, constants, logger, AppConfig
│   ├── data/                   # JSON loader ($ref resolution, parameter expansion), validators, condition_evaluator
│   ├── driver/                 # WebDriver factory and lifecycle (Chrome / Firefox / Edge)
│   ├── locators/               # Locator resolver: JSON → Selenium By
│   ├── models/                 # Pydantic domain models (workflow_models, element_models)
│   ├── ui/                     # BasePage, BaseComponent, DynamicPage, DynamicSection
│   ├── utils/                  # File helpers, string utilities, screenshot manager, coverage_index
│   ├── waits/                  # wait_manager, expected_states, ajax_monitor, page_readiness
│   └── workflow/               # workflow_engine, navigator, result_collector, execution_context
├── testdata/
│   └── workflows/              # Workflow JSON files
│       ├── sample_workflow.json
│       ├── onboarding_workflow.json
│       ├── tabs/               # Reusable tab definitions (referenced via $ref)
│       ├── pages/              # Reusable page definitions (referenced via $ref)
│       └── sections/           # Reusable section definitions (referenced via $ref)
├── tests/
│   ├── conftest.py             # Pytest fixtures and CLI options
│   ├── unit/                   # Unit tests — no browser required (394 tests)
│   └── smoke/                  # End-to-end tests — real browser
├── .env.example
├── pytest.ini
├── pyproject.toml
└── requirements.txt
```

---

## Extending the Framework

### Add a custom placeholder token

Add a zero-argument generator function and register it in `PLACEHOLDER_REGISTRY` inside [src/actions/value_resolver.py](src/actions/value_resolver.py). No other files need to change.

```python
# src/actions/value_resolver.py

def generate_today_iso() -> str:
    from datetime import date
    return date.today().isoformat()

PLACEHOLDER_REGISTRY: Dict[str, Callable[[], str]] = {
    # ... existing entries ...
    "today_iso": generate_today_iso,
}
```

Usage in workflow JSON:

```json
{ "value": "${today_iso}" }
```

### Add a custom wait condition

1. Add a value to `WaitConditionType` in [src/core/enums.py](src/core/enums.py)
2. Add the callable implementation in [src/waits/expected_states.py](src/waits/expected_states.py)
3. Handle the new enum value in the `_dispatch` method of [src/waits/wait_manager.py](src/waits/wait_manager.py)

### Add a custom element action

1. Add a value to `ActionType` in [src/core/enums.py](src/core/enums.py)
2. Add a branch in `ElementActions.execute()` in [src/actions/element_actions.py](src/actions/element_actions.py)
