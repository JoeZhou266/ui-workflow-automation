# Phase 13: Generate HTML Test Report - Research

**Researched:** 2026-05-30
**Domain:** pytest-html 4.x plugin API, pytest hook ordering, HTML report generation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Report shows **both levels**: pytest test-level summary (header/summary table) AND per-test workflow step detail (expandable drill-down from `ResultCollector.summary()`).
- **D-02:** Per-test drill-down shows **all steps** with status — PASSED (green), FAILED (red), SKIPPED (yellow) — including Tab→Page→Section→Element hierarchy, action type, and `duration_ms`. On FAILED steps: also show `error_message` and `failure_phase`.
- **D-03:** Use **pytest-html** (already installed at 4.2.0) as the base report generator. Extend it via pytest-html plugin hooks to inject the per-test workflow step details as an expandable section in each test row.
- **D-04:** Do NOT use Allure.
- **D-05:** Screenshots from `reports/screenshots/` are shown as **clickable linked thumbnails** on FAILED steps where `screenshot_path` is present on the `StepResult`. Use relative paths so links resolve when the HTML and `screenshots/` folder are in the same `reports/` directory.
- **D-06:** Videos from `reports/videos/` are shown as **linked filenames** (not embedded) on FAILED tests where a video path is available. Relative paths from `reports/`.
- **D-07:** Both artifact links appear only where the artifact actually exists — no broken links.
- **D-08:** Report is **always auto-generated** on every pytest run. Configure via `--html` and `--self-contained-html` flags via `conftest.py` hook — no opt-in flag required.
- **D-09:** **Timestamped per run**, flat in `reports/`. Format: `<workflow_name>_report_<YYYYMMDD_HHMMSS>.html`. Prefix `run` when no `--workflow` option is provided.
- **D-10:** Files accumulate in `reports/` — no auto-cleanup.

### Claude's Discretion

- Where exactly to hook into pytest-html's plugin API (exact hook names, extras format) — verified below.
- How `ResultCollector.summary()` is passed to the conftest hook — via fixture, stash, or direct import of a module-level collector. Follow existing `_phase_report_key` stash pattern in `conftest.py`.
- `.gitignore` update: add `reports/*.html` (keep `reports/.gitkeep`).
- Unit tests: cover the report generation logic (not the full HTML output, but the data transformation from `ExecutionSummary` to the extras structure).

### Deferred Ideas (OUT OF SCOPE)

- Latest symlink (`reports/report.html` → latest timestamped file)
- Allure report activation
- Report auto-cleanup (keep last N)
- Base64 screenshot embedding
- JSON export alongside HTML
</user_constraints>

---

## Summary

Phase 13 extends the existing pytest infrastructure with automatic HTML test reports powered by pytest-html 4.2.0 (already installed). The core challenge is threefold: (1) generating a dynamically timestamped report filename on every run without a static `addopts` entry, (2) injecting per-test workflow step drill-down HTML into each pytest-html test row, and (3) correctly passing `ExecutionSummary` data from the test body to the plugin hook that renders the HTML.

All three challenges have verified solutions. The dynamic filename is set via a `pytest_configure` hook in `conftest.py` (executed before pytest-html reads `config.option.htmlpath`). The drill-down HTML is injected via `pytest_html.extras.html()` appended to `report.extras` on the teardown-phase report — which pytest-html's `_process_extras` includes in `processed_extras` for the test row. The `ExecutionSummary` is passed from the smoke test through `item.stash` (new `StashKey`) read in `conftest.py`'s existing `pytest_runtest_makereport` hook extended for the teardown phase.

**Primary recommendation:** Create `src/utils/html_report.py` for the HTML-building logic (pure functions over `ExecutionSummary`), a new `HTML_REPORT_DIR` constant in `src/core/constants.py`, a `pytest_configure` hook in `conftest.py` for dynamic filename wiring, and extend the existing `pytest_runtest_makereport` hook in `conftest.py` to attach extras on the teardown phase.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTML step-table generation | Utility module (`src/utils/html_report.py`) | — | Pure transform: `ExecutionSummary` → HTML string; no pytest coupling |
| Dynamic report path generation | `tests/conftest.py` (pytest_configure hook) | `src/core/constants.py` | Must run before pytest-html reads `htmlpath`; constants define defaults |
| Extras injection (per-test drill-down) | `tests/conftest.py` (makereport hook extension) | — | Only hook with access to both `item` and `report` at teardown time |
| ExecutionSummary hand-off from test | `tests/conftest.py` (new StashKey + fixture) | Smoke test body | Stash is the established pattern for per-test cross-hook data |
| Screenshot/video relative path calc | `src/utils/html_report.py` | — | Isolated path logic; tested independently |
| Report directory management | `src/core/constants.py` + `src/utils/files.py` | `tests/conftest.py` | Reuse `ensure_dir`, constant for default path |
| `.gitignore` update | `.gitignore` (already has `reports/*.html`) | — | Already present — no action needed |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-html | 4.2.0 | Base report generator | Already installed; D-03 locked |
| pytest-metadata | 3.1.1 | Environment table in report | Required by pytest-html 4.x |
| jinja2 | (installed as pytest-html dep) | pytest-html uses internally | No direct use by our code |
| pytest | 8.4.2 | Test runner; hook system | Project standard |
| pydantic | 2.13.3 | `ExecutionSummary`, `StepResult` models | Already in stack |

[VERIFIED: pip show pytest-html pytest-metadata pytest pydantic]

### Key pytest-html 4.x API (VERIFIED against installed source)

**Extras module** — `pytest_html.extras`:
```python
from pytest_html import extras
extras.html(content: str) -> dict  # FORMAT_HTML type
extras.url(content: str, name: str) -> dict
extras.image(content: str, name: str, mime_type: str, extension: str) -> dict
```

`html()` returns: `{'name': None, 'format_type': 'html', 'content': '<b>test</b>', 'mime_type': None, 'extension': None}`

**Hooks defined in `pytest_html.hooks`** (verified from installed source):
```python
def pytest_html_report_title(report): ...
def pytest_html_results_summary(prefix, summary, postfix, session): ...
def pytest_html_results_table_header(cells): ...
def pytest_html_results_table_row(report, cells): ...
def pytest_html_results_table_html(report, data): ...  # data = list of log strings
def pytest_html_duration_format(duration): ...
```

**Extras injection via `extras_stash_key`**:
```python
from pytest_html.fixtures import extras_stash_key
# pytest-html reads: item.config.stash.get(extras_stash_key, [])  during call-phase makereport
```

**Report attachment via `report.extras`**:
- pytest-html's `pytest_runtest_makereport` (call phase): `report.extras = fixture_extras + plugin_extras + deprecated_extra`
- `basereport.pytest_runtest_logreport` processes extras from ALL phases (setup, call, teardown) into `processed_extras`
- So extras on teardown-phase report ARE included in the final HTML row

[VERIFIED: direct source inspection of installed pytest-html 4.2.0]

---

## Architecture Patterns

### System Architecture Diagram

```
pytest run starts
      │
      ▼
conftest.py: pytest_configure (tryfirst=True)
      │  derives workflow_name from --workflow option
      │  builds timestamped report path
      │  sets config.option.htmlpath = "reports/<name>_report_<ts>.html"
      │  sets config.option.self_contained_html = True (or False)
      │
      ▼
pytest-html: pytest_configure
      │  reads config.option.htmlpath (already set above)
      │  registers Report plugin for the session
      │
      ▼
test collection & execution
      │
      ├── smoke test body executes
      │       WorkflowEngine.run() → ExecutionSummary
      │       stores summary in request.node.stash[_execution_summary_key]
      │
      ├── conftest: pytest_runtest_makereport (existing, extended)
      │       when=call: stores phase report in stash (existing behavior)
      │       when=teardown: reads _execution_summary_key from item.stash
      │                      builds HTML table via html_report.build_step_table(summary)
      │                      appends pytest_html.extras.html(html_str) to rep.extras
      │
      └── pytest-html: pytest_runtest_logreport (trylast)
              collects extras from setup + call + teardown reports
              renders HTML row with drill-down extras embedded
      │
      ▼
pytest-html: pytest_sessionfinish
      Writes final HTML to reports/<name>_report_<YYYYMMDD_HHMMSS>.html
```

### Recommended Project Structure

New files created in this phase:

```
src/
└── utils/
    └── html_report.py      # Pure functions: ExecutionSummary → HTML string
        ├── build_step_table(summary, reports_dir) -> str
        └── _step_row_html(step, reports_dir) -> str

tests/
└── unit/
    └── test_html_report.py # Unit tests for html_report.py functions

tests/
└── conftest.py             # Extended (not replaced):
    ├── _execution_summary_key: StashKey  (new)
    ├── pytest_configure (new)            (dynamic --html path)
    └── pytest_runtest_makereport (extended teardown branch)
```

Existing files modified:

```
src/core/constants.py       # Add: HTML_REPORT_DIR = "reports"
                            # Add: HTML_REPORT_DATE_FORMAT = "%Y%m%d_%H%M%S"
configs/env.*.yaml          # Optionally: html_reports_dir: reports  (follows video/screenshot pattern)
src/core/config.py          # Optionally: self.html_reports_dir = ...
.gitignore                  # Already has reports/*.html — NO CHANGE NEEDED
```

### Pattern 1: Dynamic Report Path via pytest_configure

**What:** Set `config.option.htmlpath` to a timestamped path before pytest-html reads it.

**When to use:** When the report filename must be computed at runtime (timestamped, workflow-aware).

**Example:**
```python
# tests/conftest.py
# Source: verified against pytest-html 4.2.0 plugin.py (config.getoption("htmlpath"))

import datetime
from pathlib import Path
import pytest
from src.utils.files import ensure_dir, safe_filename

@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Set dynamic --html report path before pytest-html reads it."""
    workflow_path = config.getoption("--workflow", default=None, skip=True)
    if workflow_path:
        workflow_name = safe_filename(Path(workflow_path).stem)
    else:
        workflow_name = "run"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{workflow_name}_report_{timestamp}.html"
    report_dir = Path("reports")
    ensure_dir(report_dir)
    config.option.htmlpath = str(report_dir / filename)
    config.option.self_contained_html = True
```

**Critical:** `tryfirst=True` ensures this runs before pytest-html's own `pytest_configure` reads `htmlpath`. Without it, hook execution order is undefined (both are plain hooks).

**Note on `config.getoption` in `pytest_configure`:** The `--workflow` option is registered in `pytest_addoption`, which runs before `pytest_configure`. Use `skip=True` to avoid `ValueError` when the option isn't registered yet in some edge cases.

### Pattern 2: ExecutionSummary → Report Extras via Stash

**What:** Store the workflow `ExecutionSummary` in `item.stash` during the test, read it in the teardown-phase `pytest_runtest_makereport` hook to build and attach HTML extras.

**When to use:** When the data to be reported is produced during the test body but must be rendered by a hook that runs after the test.

**Example — StashKey and hook extension in conftest.py:**
```python
# tests/conftest.py
# Source: verified against pytest-html 4.2.0 basereport.py (teardown extras included)

from pytest import StashKey
from src.models.element_models import ExecutionSummary
from src.utils.html_report import build_step_table
from pytest_html import extras as html_extras

_execution_summary_key: StashKey[ExecutionSummary] = StashKey()

@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    rep = yield   # existing behavior
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep

    # NEW: attach workflow extras on teardown phase
    if rep.when == "teardown":
        summary = item.stash.get(_execution_summary_key, None)
        if summary is not None:
            html_str = build_step_table(summary)
            existing = getattr(rep, "extras", [])
            rep.extras = list(existing) + [html_extras.html(html_str)]

    return rep
```

**Example — fixture to store summary in stash:**
```python
# tests/conftest.py
@pytest.fixture(scope="function")
def workflow_report_extras(request):
    """Stores the ExecutionSummary in item.stash for HTML report generation.

    Usage in smoke tests:
        def test_foo(driver, workflow_definition, app_config, workflow_report_extras):
            engine = WorkflowEngine(...)
            summary = engine.run()
            workflow_report_extras(summary)   # register for HTML drill-down
    """
    _registered = []

    def _register(summary: ExecutionSummary) -> None:
        _registered.append(summary)
        request.node.stash[_execution_summary_key] = summary

    yield _register
    # teardown: nothing needed — stash was set during test body
```

**Example — smoke test usage:**
```python
# tests/smoke/test_sample_workflow.py
def test_workflow_runs_without_crash(driver, workflow_definition, app_config,
                                     workflow_report_extras):
    engine = WorkflowEngine(...)
    summary = engine.run()
    workflow_report_extras(summary)   # registers for HTML drill-down
    assert summary.failed == 0, ...
```

### Pattern 3: HTML Step Table Generation (Pure Function)

**What:** Transform `ExecutionSummary.steps` into a `<details>/<summary>` collapsible HTML block showing all steps in a color-coded table.

**When to use:** Called from `pytest_runtest_makereport` (teardown phase) to build the extras HTML string.

**Example:**
```python
# src/utils/html_report.py
# Source: ASSUMED pattern — no framework API, pure Python HTML generation

from __future__ import annotations
from html import escape
from pathlib import Path
from typing import Optional
from src.models.element_models import ExecutionSummary, StepResult
from src.core.enums import StepStatus

_STATUS_COLORS = {
    StepStatus.PASSED: "#d4edda",    # green
    StepStatus.FAILED: "#f8d7da",    # red
    StepStatus.SKIPPED: "#fff3cd",   # yellow
}


def build_step_table(summary: ExecutionSummary, reports_dir: str = "reports") -> str:
    """Return a self-contained <details> HTML block for embedding in pytest-html extras."""
    total = summary.total
    passed = summary.passed
    failed = summary.failed
    skipped = summary.skipped

    header = (
        f"Workflow: {escape(summary.workflow_name)} — "
        f"{total} steps: {passed} passed, {failed} failed, {skipped} skipped"
    )
    rows = "".join(_step_row_html(step, reports_dir) for step in summary.steps)

    return f"""
<details>
  <summary><b>{header}</b></summary>
  <table style="width:100%;border-collapse:collapse;font-size:0.85em">
    <tr>
      <th>Status</th><th>Tab</th><th>Page</th><th>Section</th>
      <th>Element</th><th>Action</th><th>Duration (ms)</th>
      <th>Error / Phase</th><th>Screenshot</th>
    </tr>
    {rows}
  </table>
</details>
"""


def _step_row_html(step: StepResult, reports_dir: str = "reports") -> str:
    color = _STATUS_COLORS.get(step.status, "#ffffff")
    duration = f"{step.duration_ms:.0f}" if step.duration_ms is not None else "—"
    error_cell = ""
    if step.status == StepStatus.FAILED:
        err = escape(step.error_message or "")
        phase = escape(str(step.failure_phase or ""))
        error_cell = f"{err}<br><small>phase: {phase}</small>"

    screenshot_cell = ""
    if step.screenshot_path:
        rel = _relative_path(step.screenshot_path, reports_dir)
        if rel:
            screenshot_cell = (
                f'<a href="{escape(rel)}" target="_blank">'
                f'<img src="{escape(rel)}" style="max-width:200px" /></a>'
            )

    return (
        f'<tr style="background:{color}">'
        f"<td>{escape(step.status.value)}</td>"
        f"<td>{escape(step.tab_name)}</td>"
        f"<td>{escape(step.page_name)}</td>"
        f"<td>{escape(step.section_name)}</td>"
        f"<td>{escape(step.element_name)}</td>"
        f"<td>{escape(step.action.value)}</td>"
        f"<td>{duration}</td>"
        f"<td>{error_cell}</td>"
        f"<td>{screenshot_cell}</td>"
        f"</tr>"
    )


def _relative_path(abs_path: str, reports_dir: str) -> Optional[str]:
    """Return path relative to reports_dir, or None if computation fails."""
    try:
        return str(Path(abs_path).relative_to(reports_dir))
    except ValueError:
        # abs_path is not under reports_dir
        return None
```

### Anti-Patterns to Avoid

- **Using fixture teardown to append to `extras` fixture:** The `extras` fixture's stash list is read by pytest-html during the call-phase `makereport` — fixture teardown runs AFTER that. Appending in teardown is too late for `extras_stash_key`. Use `report.extras` on the teardown-phase report instead (confirmed: teardown extras are included by `basereport.py`).
- **Adding `--html` to `pytest.ini` `addopts` as a static path:** This produces a fixed filename that is overwritten each run. Must use `pytest_configure` for dynamic timestamped paths.
- **Using `hookwrapper=True` style:** Deprecated in pytest 8.x. Our project uses `wrapper=True` (verified in existing `pytest_runtest_makereport`).
- **Calling `config.getoption("--workflow")` without `skip=True` in `pytest_configure`:** Raises `ValueError` if called before options are fully registered. Use `default=None, skip=True`.
- **Embedding screenshots as base64 data URIs:** Deferred per D-scope. Use relative `href`/`src` links instead.
- **Using `pytest_html_results_table_html` hook for drill-down:** Its `data` parameter is a list of log strings (plain text), not HTML. `report.extras` via `FORMAT_HTML` is the correct mechanism.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML escaping | Custom regex replace | `html.escape()` (stdlib) | Handles all HTML special chars including `"` |
| Report filename sanitization | Custom char filter | `safe_filename()` in `src/utils/files.py` | Already used by screenshot/video managers |
| Report directory creation | `os.makedirs` inline | `ensure_dir()` in `src/utils/files.py` | Idempotent, typed, matches project pattern |
| Timestamp format | `time.time()` + strftime | `datetime.datetime.now().strftime(...)` | Consistent with `SCREENSHOT_DATE_FORMAT` pattern |
| Extras dict construction | Custom dict literal | `pytest_html.extras.html(content)` | Exact format expected by pytest-html renderer |

**Key insight:** pytest-html 4.x's extras format is a specific dict structure (`{'name': ..., 'format_type': ..., 'content': ..., 'mime_type': ..., 'extension': ...}`). Never construct this dict directly — use the functions in `pytest_html.extras`.

---

## Common Pitfalls

### Pitfall 1: pytest_configure Hook Ordering

**What goes wrong:** `config.option.htmlpath` is set in `conftest.py`'s `pytest_configure`, but pytest-html's own `pytest_configure` runs first and sees `htmlpath = None`, so no report plugin is registered.

**Why it happens:** Both hooks are plain functions (no `tryfirst`/`trylast`). pytest executes them in registration order: entry-point plugins (pytest-html) register first, before conftest.py.

**How to avoid:** Decorate conftest `pytest_configure` with `@pytest.hookimpl(tryfirst=True)`. This guarantees our hook runs before pytest-html reads `htmlpath`.

**Warning signs:** pytest runs without error but no HTML file is generated. Add a terminal printout of `config.option.htmlpath` before pytest-html's configure to diagnose.

### Pitfall 2: Extras Timing (Call-Phase vs Teardown-Phase)

**What goes wrong:** Extras appended after the test body but before the teardown-phase `makereport` don't appear in the HTML. Extras appended in a fixture's teardown-after-yield may also miss the call-phase extras window.

**Why it happens:** pytest-html reads `extras_stash_key` (session-level stash) in the call-phase `makereport`. Fixture teardown runs AFTER that phase.

**How to avoid:** Use `report.extras` on the teardown-phase report. `basereport.py:pytest_runtest_logreport` collects extras from ALL phases — setup, call, teardown — into `processed_extras` before rendering. Confirmed in source:
```python
for key, reports in self._reports[report.nodeid].items():
    for each in reports:
        processed_extras += self._process_extras(each, test_id)
```

**Warning signs:** Drill-down table absent from HTML even though `build_step_table()` was called.

### Pitfall 3: self_contained_html and Relative Screenshot Links

**What goes wrong:** With `--self-contained-html`, pytest-html copies assets into the report. A relative `src="screenshots/foo.png"` link in an HTML extra becomes broken because the asset is not embedded.

**Why it happens:** `SelfContainedReport` only processes `FORMAT_IMAGE` extras (base64-encodes them). Raw HTML in `FORMAT_HTML` extras is included verbatim — relative links are not rewritten.

**How to avoid:** Set `config.option.self_contained_html = False` (use linked mode, not self-contained) OR use absolute paths in screenshot links. The non-self-contained `Report` class copies extra assets (JSON, TEXT) to `reports/assets/`, leaving HTML extras verbatim. Relative links work if the HTML file is in `reports/` and `screenshots/` is a subdirectory.

**Warning signs:** Images show as broken in the report.

**Resolution per D-05/D-06:** Use relative paths like `screenshots/20260530_foo.png` from the `reports/` directory. This works with non-self-contained mode. The CONTEXT.md decision to use `--self-contained-html` should be revisited: linked mode is more compatible with relative screenshot paths.

### Pitfall 4: Missing `reports/` Directory at `pytest_configure` Time

**What goes wrong:** `ensure_dir("reports")` in `pytest_configure` fails or the directory doesn't exist when the report is written.

**Why it happens:** `pytest_configure` runs at import time, before any test infrastructure is set up.

**How to avoid:** Call `ensure_dir(report_dir)` in `pytest_configure` before setting `htmlpath`. The `ensure_dir()` utility is idempotent (`mkdir(parents=True, exist_ok=True)`). The existing `reports/` directory has a `.gitkeep` but may not have `screenshots/` or `videos/` subdirectories — those are created by their respective managers.

**Warning signs:** `FileNotFoundError` when pytest-html tries to write the report.

### Pitfall 5: `config.getoption("--workflow")` in `pytest_configure`

**What goes wrong:** `AttributeError: 'option not added to parser'` when calling `config.getoption("--workflow")` in `pytest_configure` before the option has been registered.

**Why it happens:** `pytest_addoption` and `pytest_configure` hooks both fire during startup. If the option hasn't been registered yet, `getoption` raises.

**How to avoid:** Use `config.getoption("--workflow", default=None, skip=True)`. The `skip=True` argument silently returns `None` if the option is not yet registered. Alternatively, guard with `hasattr(config.option, "workflow")`.

---

## Code Examples

### Dynamic --html Path in conftest.py

```python
# tests/conftest.py
# Source: verified against pytest-html 4.2.0 plugin.py

import datetime
from pathlib import Path
import pytest
from src.utils.files import ensure_dir, safe_filename


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Dynamically set --html report path before pytest-html reads it."""
    # skip=True silently returns None if --workflow not registered yet
    workflow_path = config.getoption("--workflow", default=None, skip=True)
    if workflow_path:
        workflow_name = safe_filename(Path(workflow_path).stem)
    else:
        workflow_name = "run"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{workflow_name}_report_{timestamp}.html"
    report_dir = Path("reports")
    ensure_dir(report_dir)
    config.option.htmlpath = str(report_dir / filename)
    # Do NOT set self_contained_html=True — relative screenshot links break in that mode
    # config.option.self_contained_html = False  (default, no need to set)
```

### StashKey Declaration and Hook Extension

```python
# tests/conftest.py — additions
from pytest import StashKey
from src.models.element_models import ExecutionSummary
from src.utils.html_report import build_step_table
from pytest_html import extras as html_extras

_execution_summary_key: StashKey[ExecutionSummary] = StashKey()

# EXTEND existing pytest_runtest_makereport (don't replace):
@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    rep = yield
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep

    # Attach workflow step drill-down on teardown phase
    if rep.when == "teardown":
        summary = item.stash.get(_execution_summary_key, None)
        if summary is not None:
            html_str = build_step_table(summary)
            existing = list(getattr(rep, "extras", []) or [])
            rep.extras = existing + [html_extras.html(html_str)]

    return rep
```

### workflow_report_extras Fixture

```python
# tests/conftest.py — new fixture (function-scoped, opt-in)
@pytest.fixture(scope="function")
def workflow_report_extras(request):
    """Register an ExecutionSummary for per-test HTML drill-down.

    Opt-in: tests must request this fixture explicitly.
    Usage:
        def test_foo(driver, workflow_definition, app_config, workflow_report_extras):
            summary = engine.run()
            workflow_report_extras(summary)
    """
    def _register(summary: ExecutionSummary) -> None:
        request.node.stash[_execution_summary_key] = summary

    yield _register
```

### pytest-html extras.html() Verified Signature

```python
# Source: pytest_html/extras.py (installed 4.2.0)
from pytest_html import extras

# Build HTML extra dict:
extra_item = extras.html("<b>my content</b>")
# Returns: {'name': None, 'format_type': 'html', 'content': '<b>my content</b>',
#           'mime_type': None, 'extension': None}

# Attach to report in makereport:
rep.extras = list(getattr(rep, "extras", []) or []) + [extra_item]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `report.extra` attribute on report | `report.extras` (plural) | pytest-html 4.x | Old API deprecated; raises `DeprecationWarning` in 4.x |
| `extra` fixture | `extras` fixture (plural) | pytest-html 4.x | Both exist but `extra` issues warning |
| `hookwrapper=True` in `pytest.hookimpl` | `wrapper=True` | pytest 8.x | `hookwrapper=True` still works but deprecated |
| `pytest_html_results_table_row` cells manipulation | `report.extras` with `FORMAT_HTML` | 4.x architecture change | `cells` are now HTML strings; extras are separate |

**Deprecated/outdated:**
- `report.extra` (singular): Use `report.extras`. The 4.x plugin still reads it but warns.
- `extra` fixture: Use `extras` fixture. Both exist; `extra` fixture issues `DeprecationWarning`.
- `hookwrapper=True`: Use `wrapper=True`. Already correct in this project's existing hook.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `config.option.htmlpath` can be set as an attribute on `config.option` in `pytest_configure` and pytest-html's own `pytest_configure` will read it as if `--html` was passed | Architecture Patterns / Pattern 1 | If wrong, report not generated; workaround: use environment variable or create a custom plugin class |
| A2 | `tryfirst=True` on conftest `pytest_configure` guarantees it runs before pytest-html's plain `pytest_configure` | Pattern 1 | If wrong, need `trylast=True` on pytest-html side or a different mechanism |
| A3 | `report.extras` set on a teardown-phase report is included in the final HTML row via `basereport._process_extras` | Pattern 2 | If wrong, need to use call-phase extras instead (requires test body to build HTML) |
| A4 | Non-self-contained report mode (default) preserves relative `href`/`src` links in `FORMAT_HTML` extras verbatim | Common Pitfalls / Pitfall 3 | If wrong, screenshot links always broken; workaround: use absolute paths or omit screenshots |

**Note:** A1–A3 were cross-verified against the installed pytest-html 4.2.0 source code directly. Risk is LOW. A4 is verified from source: `FORMAT_HTML` extras bypass all asset processing in `_process_extras` (only `FORMAT_JSON`, `FORMAT_TEXT`, `FORMAT_IMAGE`, `FORMAT_VIDEO` are processed).

[VERIFIED: A4 confirmed in `basereport.py._process_extras` — `FORMAT_HTML` has no processing branch]

---

## Open Questions

1. **self_contained_html mode compatibility with relative screenshot links**
   - What we know: `--self-contained-html` mode does NOT rewrite HTML extra content; `FORMAT_IMAGE` extras are base64-encoded but raw HTML in `FORMAT_HTML` is verbatim.
   - What's unclear: D-08 mentions `--self-contained-html` in `addopts`. If used, relative `src` links in the screenshot thumbnails (inside `FORMAT_HTML` extras) will be broken because the file path is relative to the report, but the report is single-file with no adjacent `screenshots/` folder accessible.
   - Recommendation: Use **linked mode (non-self-contained)** — don't add `--self-contained-html` to `addopts`. The report file lives in `reports/` alongside `reports/screenshots/` and `reports/videos/`, so relative paths resolve correctly. If portability (emailing the HTML) is required, that is a deferred feature.

2. **Video path on the test report row (D-06)**
   - What we know: Video path is stored in the `video_recorder` fixture's teardown (as `video_path`), not in `ExecutionSummary`. D-06 says to show video link on the failed test row, not per-step.
   - What's unclear: How to get the video path into the HTML extra. The `video_recorder` fixture stores `video_path` locally; there's no current stash key for it.
   - Recommendation: Add a second StashKey `_video_path_key: StashKey[Optional[str]]` and have `video_recorder` fixture set `request.node.stash[_video_path_key] = video_path` when a video is retained (test failed). The `pytest_runtest_makereport` teardown hook can then read both `_execution_summary_key` and `_video_path_key` and embed both in the extras HTML.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest-html | Report generation | ✓ | 4.2.0 | — (locked by D-03) |
| pytest-metadata | pytest-html dependency | ✓ | 3.1.1 | — |
| pydantic | `ExecutionSummary` model | ✓ | 2.13.3 | — |
| `reports/` directory | Report output | ✓ (exists, has .gitkeep) | — | `ensure_dir()` creates it |
| Python `html.escape` | HTML entity escaping | ✓ | stdlib | — |

[VERIFIED: pip show + ls reports/]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pytest.ini` |
| Quick run command | `pytest tests/unit/test_html_report.py -x -q` |
| Full suite command | `pytest tests/unit/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HTML-01 | `build_step_table(summary)` returns valid HTML string with all step rows | unit | `pytest tests/unit/test_html_report.py::TestBuildStepTable -x` | ❌ Wave 0 |
| HTML-02 | PASSED step rows have green background color | unit | `pytest tests/unit/test_html_report.py::TestStepRowColors -x` | ❌ Wave 0 |
| HTML-03 | FAILED step rows have red background + error_message + failure_phase | unit | `pytest tests/unit/test_html_report.py::TestFailedStepRow -x` | ❌ Wave 0 |
| HTML-04 | SKIPPED step rows have yellow background | unit | `pytest tests/unit/test_html_report.py::TestSkippedStepRow -x` | ❌ Wave 0 |
| HTML-05 | Screenshot link rendered as `<a><img></a>` when `screenshot_path` is not None | unit | `pytest tests/unit/test_html_report.py::TestScreenshotLink -x` | ❌ Wave 0 |
| HTML-06 | No screenshot element when `screenshot_path` is None | unit | `pytest tests/unit/test_html_report.py::TestNoScreenshot -x` | ❌ Wave 0 |
| HTML-07 | `_relative_path()` returns correct relative path within `reports/` | unit | `pytest tests/unit/test_html_report.py::TestRelativePath -x` | ❌ Wave 0 |
| HTML-08 | `_relative_path()` returns None when path is not under `reports_dir` | unit | `pytest tests/unit/test_html_report.py::TestRelativePathOutside -x` | ❌ Wave 0 |
| HTML-09 | HTML content is escaped (no raw `<script>` injection from error messages) | unit | `pytest tests/unit/test_html_report.py::TestHtmlEscape -x` | ❌ Wave 0 |
| HTML-10 | `_execution_summary_key` StashKey exists in conftest | unit | `pytest tests/unit/test_html_report_conftest.py::TestStashKey -x` | ❌ Wave 0 |
| HTML-11 | `workflow_report_extras` fixture is function-scoped, opt-in, callable | unit | `pytest tests/unit/test_html_report_conftest.py::TestWorkflowReportExtrasFixture -x` | ❌ Wave 0 |
| HTML-12 | `pytest_configure` in conftest sets `config.option.htmlpath` with correct format | unit | `pytest tests/unit/test_html_report_conftest.py::TestPytestConfigure -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/test_html_report.py -x -q`
- **Per wave merge:** `pytest tests/unit/ -v`
- **Phase gate:** Full suite green (`pytest tests/unit/ -v`) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_html_report.py` — covers HTML-01 through HTML-09 (pure function tests)
- [ ] `tests/unit/test_html_report_conftest.py` — covers HTML-10 through HTML-12 (conftest structure tests)
- No framework install needed — pytest already configured

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `html.escape()` on all `StepResult` string fields before embedding in HTML |
| V6 Cryptography | no | — |

### Known Threat Patterns for HTML Generation

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via unsanitized error_message | Tampering | `html.escape()` on every `StepResult` string field in `_step_row_html()` |
| XSS via workflow/element names from JSON | Tampering | Same: `html.escape()` on `tab_name`, `page_name`, `section_name`, `element_name` |
| Path traversal via screenshot_path | Tampering | `Path.relative_to()` raises `ValueError` if path escapes `reports_dir`; returns `None` |

**Note:** Reports are local developer artifacts, not served over HTTP. XSS risk is low but `html.escape()` is trivial to apply and prevents unintended rendering if the HTML is ever opened in a browser.

---

## Sources

### Primary (HIGH confidence)

- Installed `pytest_html` 4.2.0 source — `/Users/.../site-packages/pytest_html/` — hooks.py, extras.py, plugin.py, fixtures.py, basereport.py, report.py, report_data.py all directly inspected
- `tests/conftest.py` in this project — existing patterns for StashKey, hookimpl, video_recorder fixture
- `src/models/element_models.py` — `StepResult` and `ExecutionSummary` field names verified
- `src/core/constants.py`, `src/utils/files.py` — `safe_filename`, `ensure_dir` verified

### Secondary (MEDIUM confidence)

- pytest 8.4.2 hookimpl behavior (wrapper=True vs hookwrapper=True) — verified from test_conftest_hook.py assertions in this codebase
- Hook ordering guarantee for tryfirst=True conftest vs plain plugin — derived from pytest documentation behavior + source inspection

### Tertiary (LOW confidence)

- None — all critical claims verified from source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified via pip show + direct source inspection
- Architecture: HIGH — pytest-html source read directly; hook ordering verified
- Pitfalls: HIGH — discovered through systematic source tracing, not just documentation
- Test map: HIGH — derived from concrete behaviors in `html_report.py` design

**Research date:** 2026-05-30
**Valid until:** 2026-06-30 (pytest-html 4.x is stable; changes would be in changelog)
