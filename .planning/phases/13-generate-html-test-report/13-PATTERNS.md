# Phase 13: Generate HTML Test Report - Pattern Map

**Mapped:** 2026-05-30
**Files analyzed:** 7 new/modified files
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/utils/html_report.py` | utility | transform | `src/utils/screenshots.py` | role-match |
| `tests/conftest.py` | config/middleware | request-response | `tests/conftest.py` (self — extend) | exact |
| `src/core/constants.py` | config | — | `src/core/constants.py` (self — extend) | exact |
| `pytest.ini` | config | — | `pytest.ini` (self — extend) | exact |
| `.gitignore` | config | — | `.gitignore` (self — extend) | exact |
| `tests/unit/test_html_report.py` | test | transform | `tests/unit/test_video_manager.py` | role-match |
| `tests/unit/test_html_report_conftest.py` | test | request-response | `tests/unit/test_conftest_hook.py` | exact |

---

## Pattern Assignments

### `src/utils/html_report.py` (utility, transform)

**Analog:** `src/utils/screenshots.py` (same `src/utils/` package, same utility role, same `ensure_dir`/`safe_filename` dependencies, same constant + logger setup)

**Imports pattern** (`src/utils/screenshots.py` lines 1–13):
```python
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.constants import SCREENSHOT_DATE_FORMAT, SCREENSHOT_DIR
from src.core.logger import get_logger
from src.utils.files import ensure_dir, safe_filename

logger = get_logger("screenshots")
```

Adapt for `html_report.py`:
```python
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Optional

from src.core.constants import HTML_REPORT_DIR
from src.core.enums import StepStatus
from src.models.element_models import ExecutionSummary, StepResult
```

**Core transform pattern** — `src/utils/screenshots.py` lines 17–52 show the class-level pattern; `html_report.py` uses module-level pure functions instead (no class needed since there is no state). Follow the same guard/fallback shape used in `VideoManager.start()` (`src/utils/videos.py` lines 31–76): guard early, return `None` on failure, log with `logger.warning`.

**Error handling / fallback pattern** (`src/utils/videos.py` lines 62–76):
```python
        try:
            self._proc = subprocess.Popen(...)
            self._current_path = str(file_path)
            logger.info("Video recording started: %s", file_path)
            return self._current_path
        except FileNotFoundError:
            logger.warning("ffmpeg not found — video recording disabled")
            return None
        except Exception as exc:
            logger.warning("Failed to start video recording '%s': %s", name, exc)
            return None
```

Adapt for `_relative_path()`: wrap `Path.relative_to()` in try/except `ValueError`, return `None` on failure (path escapes `reports_dir`). This exactly matches the security requirement from RESEARCH.md.

**Filename/timestamp pattern** (`src/utils/screenshots.py` lines 38–42):
```python
        timestamp = datetime.now().strftime(SCREENSHOT_DATE_FORMAT)
        safe_name = safe_filename(name)
        filename = f"{timestamp}_{safe_name}.png"

        target_dir = self._base_dir / subdirectory if subdirectory else self._base_dir
        ensure_dir(target_dir)
```

For report naming in `pytest_configure`, use same `safe_filename` + `strftime(HTML_REPORT_DATE_FORMAT)` pattern.

**Status color constants** — Follow the inline constant dict pattern used for enums elsewhere. Use `StepStatus` enum values as keys (same pattern as `src/core/enums.py`):
```python
_STATUS_COLORS = {
    StepStatus.PASSED: "#d4edda",
    StepStatus.FAILED: "#f8d7da",
    StepStatus.SKIPPED: "#fff3cd",
}
```

---

### `tests/conftest.py` — extensions (middleware/config, request-response)

**Analog:** `tests/conftest.py` itself — the file is extended in-place; all additions must match existing style exactly.

**StashKey declaration pattern** (`tests/conftest.py` lines 13–17):
```python
from pytest import CollectReport, StashKey

# ---------------------------------------------------------------------------
# Test outcome stash (populated by hook, read by video_recorder teardown)
# ---------------------------------------------------------------------------

_phase_report_key: StashKey[dict[str, CollectReport]] = StashKey()
```

New `_execution_summary_key` follows the identical pattern — module-level `StashKey` with type annotation:
```python
from src.models.element_models import ExecutionSummary

_execution_summary_key: StashKey[ExecutionSummary] = StashKey()
```

**Hook wrapper pattern** (`tests/conftest.py` lines 20–25):
```python
@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Store each phase report in item.stash so fixtures can read pass/fail outcome."""
    rep = yield   # new-style wrapper — yield returns the report directly
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep
    return rep
```

The existing hook body must be kept intact. The teardown extension appends after the existing `item.stash.setdefault(...)` line — do NOT replace the hook, extend it:
```python
@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    rep = yield
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep

    # NEW: attach workflow step drill-down on teardown phase
    if rep.when == "teardown":
        summary = item.stash.get(_execution_summary_key, None)
        if summary is not None:
            html_str = build_step_table(summary)
            existing = list(getattr(rep, "extras", []) or [])
            rep.extras = existing + [html_extras.html(html_str)]

    return rep
```

**New `pytest_configure` hook** — must use `@pytest.hookimpl(tryfirst=True)` (no `wrapper`) to set `config.option.htmlpath` before pytest-html reads it. Pattern for `config.getoption` with `skip=True` (from RESEARCH.md, verified against pytest-html 4.2.0 source):
```python
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Dynamically set --html report path before pytest-html reads it."""
    workflow_path = config.getoption("--workflow", default=None, skip=True)
    if workflow_path:
        workflow_name = safe_filename(Path(workflow_path).stem)
    else:
        workflow_name = "run"
    timestamp = datetime.datetime.now().strftime(HTML_REPORT_DATE_FORMAT)
    filename = f"{workflow_name}_report_{timestamp}.html"
    report_dir = Path(HTML_REPORT_DIR)
    ensure_dir(report_dir)
    config.option.htmlpath = str(report_dir / filename)
    # Do NOT set self_contained_html=True — relative screenshot links break in that mode
```

**Opt-in fixture pattern** (`tests/conftest.py` lines 91–128 — `video_recorder` fixture):
```python
@pytest.fixture(scope="function")
def video_recorder(request, app_config: AppConfig, driver):
    """Start video recording; retain file only on test failure.

    Opt-in: tests must explicitly request this fixture.
    ...
    """
    ...
    yield video_path

    # --- teardown: read outcome from stash ---
    report = request.node.stash.get(_phase_report_key, {})
    ...
```

New `workflow_report_extras` fixture follows identical shape — `scope="function"`, opt-in (no `autouse`), uses `request.node.stash`:
```python
@pytest.fixture(scope="function")
def workflow_report_extras(request):
    """Register an ExecutionSummary for per-test HTML drill-down.

    Opt-in: tests must request this fixture explicitly.
    Usage:
        summary = engine.run()
        workflow_report_extras(summary)
    """
    def _register(summary: ExecutionSummary) -> None:
        request.node.stash[_execution_summary_key] = summary

    yield _register
```

**Video path stash extension** — following the same `_phase_report_key` pattern, add `_video_path_key` so the `video_recorder` fixture can store a retained video path in stash for retrieval by `pytest_runtest_makereport` teardown:
```python
_video_path_key: StashKey[Optional[str]] = StashKey()
```

In `video_recorder` teardown (after `if test_failed:` block), add:
```python
        if video_path and test_failed:
            request.node.stash[_video_path_key] = video_path
```

---

### `src/core/constants.py` (config, extend in-place)

**Analog:** `src/core/constants.py` itself — append two new constants following the exact grouping + naming convention of existing constants.

**Existing constant grouping pattern** (`src/core/constants.py` lines 14–20):
```python
# Screenshot
SCREENSHOT_DIR: str = "reports/screenshots"
SCREENSHOT_DATE_FORMAT: str = "%Y%m%d_%H%M%S"

# Video
VIDEO_DIR: str = "reports/videos"
VIDEO_DATE_FORMAT: str = "%Y%m%d_%H%M%S"
```

New constants to append after the `# Video` block:
```python
# HTML Report
HTML_REPORT_DIR: str = "reports"
HTML_REPORT_DATE_FORMAT: str = "%Y%m%d_%H%M%S"
```

No other changes to this file.

---

### `pytest.ini` (config, extend in-place)

**Analog:** `pytest.ini` itself.

**Current `addopts` line** (`pytest.ini` line 14):
```ini
addopts = -v --tb=short
```

Do NOT add `--html` as a static path to `addopts` — that would produce a fixed filename overwritten each run (anti-pattern from RESEARCH.md). The dynamic path is set entirely via `pytest_configure` in `conftest.py`. No change to `pytest.ini` is needed for the HTML path.

If `pytest-html` requires `--self-contained-html` be absent (use linked mode for relative screenshot links), confirm the default is `False` and do not add it. `pytest.ini` changes for Phase 13 are: **none required**.

---

### `.gitignore` (config, verify only)

**RESEARCH.md finding:** `.gitignore` already has `reports/*.html` — confirmed no change required. The planner should verify with a read before writing, but the pattern mapper confirms this is already present per the research phase verification.

---

### `tests/unit/test_html_report.py` (test, transform)

**Analog:** `tests/unit/test_video_manager.py` — pure-function utility tests; same class-per-behavior grouping, same `from src.utils.X import Y` import pattern inside each test, same `unittest.mock.patch` usage, same `tmp_path` fixture for filesystem operations.

**Module docstring pattern** (`tests/unit/test_video_manager.py` lines 1–7):
```python
"""Unit tests for VideoManager class.

TDD RED phase — these tests must fail before implementation.
Covers: VID-01, VID-03, VID-04, VID-05
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
```

Adapt:
```python
"""Unit tests for html_report utility functions.

Covers: HTML-01 through HTML-09
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
```

**Import-inside-test pattern** (`tests/unit/test_video_manager.py` lines 19–22):
```python
    def test_video_manager_importable(self):
        from src.utils.videos import VideoManager  # noqa: F401
```

Use same style for `html_report`:
```python
class TestHtmlReportImport:
    def test_html_report_importable(self):
        from src.utils.html_report import build_step_table  # noqa: F401
```

**Fixture-based factory pattern** (`tests/unit/test_result_collector.py` lines 12–19):
```python
def _ctx(**kwargs) -> ExecutionContext:
    defaults = dict(
        workflow_name="WF",
        tab_name="Tab1",
        page_name="Page1",
        section_name="Sec1",
        element_name="El1",
    )
    defaults.update(kwargs)
    return ExecutionContext(**defaults)
```

Use same module-level factory to build `StepResult` / `ExecutionSummary` test fixtures:
```python
from src.core.enums import ActionType, FailurePhase, StepStatus
from src.models.element_models import ExecutionSummary, StepResult

def _step(status=StepStatus.PASSED, **kwargs) -> StepResult:
    defaults = dict(
        workflow_name="WF",
        tab_name="Tab1",
        page_name="Page1",
        section_name="Sec1",
        element_name="El1",
        action=ActionType.CLICK,
        status=status,
        duration_ms=42.0,
        error_message=None,
        failure_phase=None,
        screenshot_path=None,
    )
    defaults.update(kwargs)
    return StepResult(**defaults)


def _summary(steps=None) -> ExecutionSummary:
    steps = steps or []
    return ExecutionSummary(
        workflow_name="WF",
        total=len(steps),
        passed=sum(1 for s in steps if s.status == StepStatus.PASSED),
        failed=sum(1 for s in steps if s.status == StepStatus.FAILED),
        skipped=sum(1 for s in steps if s.status == StepStatus.SKIPPED),
        steps=steps,
    )
```

**Behavior-grouped class pattern** (`tests/unit/test_video_manager.py` lines 16–49):
```python
class TestVideoManagerImport:
    ...

class TestVideoManagerInterface:
    ...

class TestVideoManagerHeadless:
    ...
```

Apply same grouping to cover HTML-01 through HTML-09:
```python
class TestBuildStepTable:          # HTML-01: returns valid HTML with all step rows
class TestStepRowColors:           # HTML-02: PASSED=green, FAILED=red, SKIPPED=yellow
class TestFailedStepRow:           # HTML-03: error_message + failure_phase on FAILED rows
class TestSkippedStepRow:          # HTML-04: yellow background on SKIPPED
class TestScreenshotLink:          # HTML-05: <a><img></a> when screenshot_path set
class TestNoScreenshot:            # HTML-06: no <img> when screenshot_path is None
class TestRelativePath:            # HTML-07: correct relative path within reports/
class TestRelativePathOutside:     # HTML-08: returns None when path not under reports_dir
class TestHtmlEscape:              # HTML-09: html.escape() prevents <script> injection
```

---

### `tests/unit/test_html_report_conftest.py` (test, request-response)

**Analog:** `tests/unit/test_conftest_hook.py` — identical pattern: `import tests.conftest as conftest`, inspect module attributes and hookimpl markers, no real pytest session needed.

**Module-level import pattern** (`tests/unit/test_conftest_hook.py` lines 1–9):
```python
"""
Tests for the pytest_runtest_makereport hook and StashKey constant added to conftest.py.
TDD RED: these tests fail until conftest.py is updated.
"""
from __future__ import annotations

import tests.conftest as conftest
from pytest import StashKey
```

Adapt identically for conftest extension tests.

**StashKey existence check pattern** (`tests/unit/test_conftest_hook.py` lines 12–22):
```python
class TestStashKeyConstant:
    """_phase_report_key must be a StashKey instance at module level."""

    def test_phase_report_key_exists(self):
        assert hasattr(conftest, "_phase_report_key"), (
            "_phase_report_key not found in tests/conftest.py"
        )

    def test_phase_report_key_is_stashkey(self):
        assert isinstance(conftest._phase_report_key, StashKey), (
            f"_phase_report_key is {type(conftest._phase_report_key)}, expected StashKey"
        )
```

Apply same check for `_execution_summary_key`:
```python
class TestExecutionSummaryStashKey:
    def test_execution_summary_key_exists(self):
        assert hasattr(conftest, "_execution_summary_key")

    def test_execution_summary_key_is_stashkey(self):
        assert isinstance(conftest._execution_summary_key, StashKey)
```

**hookimpl marker check pattern** (`tests/unit/test_conftest_hook.py` lines 38–49):
```python
    def test_hook_has_hookimpl_marker(self):
        hook = conftest.pytest_runtest_makereport
        assert hasattr(hook, "pytest_impl"), (...)
        opts = hook.pytest_impl
        assert opts.get("wrapper") is True, f"wrapper=True not set; opts={opts}"
        assert opts.get("tryfirst") is True, f"tryfirst=True not set; opts={opts}"
```

For `pytest_configure`, check `tryfirst=True` but NOT `wrapper=True` (it's a plain hookimpl, not a wrapper):
```python
class TestPytestConfigure:
    def test_configure_hook_exists(self):
        assert hasattr(conftest, "pytest_configure")

    def test_configure_hook_has_tryfirst(self):
        hook = conftest.pytest_configure
        opts = getattr(hook, "pytest_impl", {})
        assert opts.get("tryfirst") is True
```

**Fixture introspection pattern** (`tests/unit/test_conftest_video_recorder.py` lines 30–57):
```python
    def test_fixture_not_autouse(self):
        marker = getattr(conftest.video_recorder, "_pytestfixturefunction", None)
        if marker is not None:
            assert not marker.autouse, "video_recorder must not be autouse"

    def test_fixture_scope_function(self):
        marker = getattr(conftest.video_recorder, "_pytestfixturefunction", None)
        if marker is not None:
            assert marker.scope in ("function", None), (...)
```

Apply same `_pytestfixturefunction` marker checks for `workflow_report_extras`:
```python
class TestWorkflowReportExtrasFixture:
    def test_fixture_exists(self):
        assert hasattr(conftest, "workflow_report_extras")

    def test_fixture_not_autouse(self):
        marker = getattr(conftest.workflow_report_extras, "_pytestfixturefunction", None)
        if marker is not None:
            assert not marker.autouse

    def test_fixture_scope_function(self):
        marker = getattr(conftest.workflow_report_extras, "_pytestfixturefunction", None)
        if marker is not None:
            assert marker.scope in ("function", None)

    def test_fixture_is_callable(self):
        assert callable(conftest.workflow_report_extras)
```

---

## Shared Patterns

### `from __future__ import annotations` Header
**Source:** Every existing Python source file in `src/` and `tests/`
**Apply to:** `src/utils/html_report.py`, `tests/unit/test_html_report.py`, `tests/unit/test_html_report_conftest.py`
```python
from __future__ import annotations
```
All new Python files must begin with this import — project-wide convention enforced by CLAUDE.md.

### Constants Import Convention
**Source:** `src/utils/screenshots.py` lines 9–10, `src/utils/videos.py` lines 12–13
```python
from src.core.constants import SCREENSHOT_DATE_FORMAT, SCREENSHOT_DIR
from src.core.logger import get_logger
```
New `html_report.py` must import `HTML_REPORT_DIR` and `HTML_REPORT_DATE_FORMAT` from `src.core.constants` — never hardcode the string `"reports"` inline.

### `ensure_dir` + `safe_filename` Usage
**Source:** `src/utils/files.py` lines 6–16; used identically in `screenshots.py` lines 12, 39–44 and `videos.py` lines 13, 56
```python
from src.utils.files import ensure_dir, safe_filename

timestamp = datetime.now().strftime(SCREENSHOT_DATE_FORMAT)
safe_name = safe_filename(name)
filename = f"{timestamp}_{safe_name}.png"
ensure_dir(target_dir)
```
`pytest_configure` must call `ensure_dir(report_dir)` before setting `config.option.htmlpath`. Report filename must use `safe_filename(workflow_stem)` + `strftime(HTML_REPORT_DATE_FORMAT)`.

### StashKey Module-Level Declaration
**Source:** `tests/conftest.py` lines 13–17
```python
_phase_report_key: StashKey[dict[str, CollectReport]] = StashKey()
```
All new StashKeys (`_execution_summary_key`, `_video_path_key`) declared at module level with type annotations immediately adjacent to their section comment block.

### Opt-In Fixture Shape
**Source:** `tests/conftest.py` lines 91–128 (`video_recorder`)
- `scope="function"`, no `autouse`
- Reads `request.node.stash` for cross-hook communication
- Uses `yield` (generator fixture) even when teardown is trivial
- Includes docstring explaining opt-in usage

### `wrapper=True, tryfirst=True` Hook Style
**Source:** `tests/conftest.py` lines 20–25
```python
@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    rep = yield
    ...
    return rep
```
Never use `hookwrapper=True` (deprecated in pytest 8.x). `pytest_configure` is NOT a wrapper hook — use `@pytest.hookimpl(tryfirst=True)` only.

### Test Class Naming Convention
**Source:** `tests/unit/test_video_manager.py`, `tests/unit/test_conftest_hook.py`
- Class names: `TestXxxBehavior` pattern
- Method names: `test_<what>_<condition>`
- Imports inside test methods (not at module level for source under test)
- `setup_method` for class-level instance setup (see `tests/unit/test_result_collector.py` line 24)

---

## No Analog Found

All files have analogs in the codebase. No files require falling back to RESEARCH.md patterns exclusively.

---

## Metadata

**Analog search scope:** `tests/conftest.py`, `tests/unit/`, `src/utils/`, `src/core/`, `pytest.ini`, `src/models/element_models.py`
**Files scanned:** 14
**Pattern extraction date:** 2026-05-30
