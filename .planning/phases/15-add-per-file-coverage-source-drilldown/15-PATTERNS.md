# Phase 15: Add Per-File Coverage Source Drilldown - Pattern Map

**Mapped:** 2026-05-31
**Files analyzed:** 6
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `.coveragerc` | config | batch | `.coveragerc` (self — modify existing) | exact |
| `tests/conftest.py` | middleware/hook | event-driven | `tests/conftest.py` (self — extend existing) | exact |
| `src/core/constants.py` | config | — | `src/core/constants.py` (self — extend existing) | exact |
| `src/utils/coverage_index.py` | utility | transform | `src/utils/html_report.py` | role-match |
| `tests/unit/test_coverage_index.py` | test | — | `tests/unit/test_html_report.py` | exact |
| `tests/unit/test_coverage_conftest.py` | test | — | `tests/unit/test_html_report_conftest.py` | exact |

---

## Pattern Assignments

### `.coveragerc` (config, batch)

**Analog:** `.coveragerc` (existing file — single line addition)

**Existing content** (lines 1-7):
```ini
[run]
source = src
omit =
    src/**/__init__.py

[html]
directory = reports/coverage
```

**Change:** Add `branch = true` as the last line under `[run]`, before the blank line separating `[run]` from `[html]`:
```ini
[run]
source = src
omit =
    src/**/__init__.py
branch = true

[html]
directory = reports/coverage
```

No other sections or keys change. No code changes are triggered by this edit alone — coverage.py handles branch instrumentation automatically at runtime.

---

### `tests/conftest.py` (middleware/hook, event-driven)

**Analog:** `tests/conftest.py` (existing file — two additions)

**Existing imports pattern** (lines 1-18):
```python
from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Optional

import pytest
from pytest import CollectReport, StashKey
from pytest_html import extras as html_extras

from src.core.config import AppConfig
from src.core.constants import HTML_REPORT_DATE_FORMAT, HTML_REPORT_DIR
from src.core.logger import configure_logging
from src.models.element_models import ExecutionSummary
from src.utils.files import ensure_dir, safe_filename
from src.utils.html_report import build_step_table
```

**Addition 1 — extend imports** (add to existing import block):
```python
from src.core.constants import COVERAGE_DIR, HTML_REPORT_DATE_FORMAT, HTML_REPORT_DIR
from src.utils.coverage_index import build_custom_index
```

**Addition 2 — extend `pytest_runtest_makereport` teardown block** (lines 59-82):

The existing teardown block (lines 65-80) already builds `html_parts` and appends extras. The coverage link is inserted into `html_parts` after the video-path block, before the `html_str` join:

```python
# Existing pattern (lines 65-80) — teardown extras block:
if rep.when == "teardown":
    summary = item.stash.get(_execution_summary_key, None)
    video_path = item.stash.get(_video_path_key, None)
    if summary is not None or video_path is not None:
        html_parts = []
        if summary is not None:
            html_parts.append(build_step_table(summary))
        if video_path is not None:
            rel = Path(video_path).name
            html_parts.append(
                f'<p><a href="videos/{rel}" target="_blank">&#9654; Video</a></p>'
            )
        # NEW: Coverage link (D-08, D-09, D-10)
        coverage_index = Path(HTML_REPORT_DIR) / "coverage" / "index.html"
        if coverage_index.exists():
            html_parts.append(
                '<p><a href="coverage/index.html" target="_blank">Coverage Report</a></p>'
            )
        html_str = "".join(html_parts)
        existing = list(getattr(rep, "extras", []) or [])
        rep.extras = existing + [html_extras.html(html_str)]
```

**Addition 3 — new `pytest_sessionfinish` hook** (append after the `pytest_runtest_makereport` function):

The hook lifecycle pattern mirrors `pytest_configure` (plain hook, not a wrapper). The fail-open pattern (warn, never crash) mirrors `VideoManager.start()`:

```python
def pytest_sessionfinish(session, exitstatus):
    """Generate custom_index.html after coverage HTML is written (D-13).

    Hook ordering: pytest-cov writes coverage HTML inside pytest_runtestloop
    (before pytest_sessionfinish fires), so reports/coverage/ and .coverage
    are both available here.

    Fail-open: any exception warns and skips generation; never fails the session.
    """
    config = session.config
    # D-11: respect --no-cov (pytest-cov stores this as config.option.no_cov)
    if getattr(config.option, "no_cov", False):
        return

    # D-14: skip gracefully when .coverage binary doesn't exist
    if not Path(".coverage").exists():
        return

    try:
        html = build_custom_index(coverage_dir=COVERAGE_DIR)
        out = Path(COVERAGE_DIR) / "custom_index.html"
        out.write_text(html, encoding="utf-8")
    except Exception as exc:
        import warnings
        warnings.warn(f"coverage_index: failed to generate custom_index.html: {exc}")
```

---

### `src/core/constants.py` (config, —)

**Analog:** `src/core/constants.py` (existing file — append two lines)

**Existing constant pattern** (lines 14-24):
```python
# Screenshot
SCREENSHOT_DIR: str = "reports/screenshots"
SCREENSHOT_DATE_FORMAT: str = "%Y%m%d_%H%M%S"

# Video
VIDEO_DIR: str = "reports/videos"
VIDEO_DATE_FORMAT: str = "%Y%m%d_%H%M%S"

# HTML Report
HTML_REPORT_DIR: str = "reports"
HTML_REPORT_DATE_FORMAT: str = "%Y%m%d_%H%M%S"
```

**Addition** (append after the HTML Report block, before the Retry block):
```python
# Coverage
COVERAGE_DIR: str = "reports/coverage"
```

Pattern: one-line comment header + `NAME: str = "path/string"`. No trailing comma. Mirrors `SCREENSHOT_DIR`, `VIDEO_DIR`, `HTML_REPORT_DIR` exactly.

---

### `src/utils/coverage_index.py` (utility, transform)

**Analog:** `src/utils/html_report.py`

**Imports pattern** from `html_report.py` (lines 1-10):
```python
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Optional

from src.core.constants import HTML_REPORT_DIR
from src.core.enums import StepStatus
from src.models.element_models import ExecutionSummary, StepResult
```

**New file imports pattern** (adapt from analog):
```python
from __future__ import annotations

import glob
import os
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional

import coverage
from coverage.files import flat_rootname
```

**Core transform pattern** from `html_report.py` — the `build_step_table()` function (lines 19-56):

The analog is a pure function that:
1. Accepts data objects + an optional directory override (for testability)
2. Builds an HTML string from sub-functions
3. Returns a `str`

`build_custom_index()` follows the same shape:
```python
def build_custom_index(
    coverage_dir: str = "reports/coverage",
    data_file: str = ".coverage",
    _cov_factory=None,   # injectable for unit tests: lambda data_file: MockCoverage()
) -> str:
    """Read .coverage binary and return HTML for reports/coverage/custom_index.html.

    Uses coverage Python API (D-14). Wraps _analyze() calls in try/except to
    fail-open if an internal API changes in a future coverage.py major version.

    Args:
        coverage_dir: Directory containing coverage HTML output (CSS discovery, output).
        data_file:    Path to .coverage binary file.
        _cov_factory: Optional callable(data_file) -> Coverage object (for testing).

    Returns:
        HTML string for custom_index.html.
    """
```

**HTML rendering sub-function pattern** from `html_report.py` — `_step_row_html()` (lines 59-103):

The analog uses private `_render_*` helpers that each take a data dict and return an HTML string. The new file follows the same pattern with `_render_html()`, `_render_package()`, `_render_row()`:
```python
def _render_html(packages: dict, css_href: str, timestamp: str, overall_pct: int) -> str:
    ...

def _render_package(pkg: str, files: list) -> str:
    # <details open> pattern (D-05): same as html_report.py's <details> usage
    return (
        "<details open>"
        f"<summary><b>{escape(pkg)}/ ({pkg_pct}%)</b> ..."
        "<table><thead>...</thead>"
        f"<tbody>{rows}</tbody></table>"
        "</details>"
    )

def _render_row(f: dict) -> str:
    # Mirrors _step_row_html — one <tr> per data item, escape all user-data fields
    return (
        "<tr>"
        f'<td><a href="{escape(f["url"])}">{escape(f["rel"])}</a></td>'
        ...
        "</tr>"
    )
```

**Error handling pattern** from `src/utils/videos.py` (lines 61-76) — fail-open with logger.warning:
```python
try:
    ...
except Exception as exc:
    import warnings
    warnings.warn(f"coverage_index: {exc}")
```

`coverage_index.py` uses `warnings.warn` (not logger) because it runs in `pytest_sessionfinish` where the logger may not be initialized; mirrors conftest convention.

**Package grouping helper** (pure function, no analog — novel logic):
```python
def _package_from_path(rel_path: str) -> str:
    """Extract package name from relative path: 'src/actions/x.py' -> 'actions'."""
    parts = rel_path.replace("\\", "/").split("/")
    return parts[1] if len(parts) > 2 else "root"
```

---

### `tests/unit/test_coverage_index.py` (test, —)

**Analog:** `tests/unit/test_html_report.py`

**File header pattern** (lines 1-13):
```python
"""Unit tests for html_report utility functions.

Covers: HTML-01 through HTML-09
"""
from __future__ import annotations

import pytest
```

New file follows the same pattern:
```python
"""Unit tests for coverage_index utility.

Covers: COV-01 through COV-06, COV-10, COV-11
"""
from __future__ import annotations

import pytest
```

**Inline import pattern** from `test_html_report.py` (lines 58-60, 109-110, etc.):

All imports from `src.*` are done inside test methods, not at module level. This catches import errors as test failures rather than collection errors:
```python
class TestBuildStepTable:
    def test_returns_details_block(self):
        from src.utils.html_report import build_step_table
        ...
```

New file uses the same pattern:
```python
class TestBuildCustomIndex:
    def test_returns_html_string(self):
        from src.utils.coverage_index import build_custom_index
        ...
```

**Factory function pattern** from `test_html_report.py` (lines 14-49):

Module-level `_make_*()` factory functions build test data objects without importing from `src` at module level:
```python
def _make_step(status="passed", **kwargs):
    """Build a StepResult for testing. Imports src inline to catch import errors."""
    from src.core.enums import ActionType, FailurePhase, StepStatus
    from src.models.element_models import StepResult
    ...
```

New file uses a mock factory for the Coverage object:
```python
def _make_mock_coverage(files_data: dict):
    """Build a mock coverage.Coverage object for testing.

    files_data: {abs_path: {"stmts": int, "miss": int, "branch": int, "brpart": int, "pct": float}}
    """
    from unittest.mock import MagicMock
    ...
```

**Test class grouping pattern** from `test_html_report.py`:

One class per requirement ID (HTML-01 → `TestBuildStepTable`, HTML-02 → `TestPassedStepRowColor`, etc.). Each class has a docstring explaining what it covers. New file maps COV-01 through COV-11 to classes:

```python
class TestCoverageRc:       # COV-01
class TestBuildCustomIndex: # COV-02
class TestPackageGrouping:  # COV-03
class TestCssDiscovery:     # COV-04, COV-11
class TestHtmlStructure:    # COV-05, COV-06
class TestMissingCoverageFile: # COV-10
```

**Assert pattern** from `test_html_report.py`:

Assertions check HTML string content rather than DOM parsing. Error messages follow the template `"<assertion noun> must <expected>; got <actual>"`:
```python
assert "<details>" in html
assert "WF" in html
assert "#d4edda" in html, f"Expected green background; got: {html[:200]}"
```

---

### `tests/unit/test_coverage_conftest.py` (test, —)

**Analog:** `tests/unit/test_html_report_conftest.py`

**File header and import pattern** (lines 1-9):
```python
"""Unit tests for Phase 13 additions to tests/conftest.py.

Covers: HTML-10 (StashKey), HTML-11 (workflow_report_extras fixture), HTML-12 (pytest_configure hook).
No real pytest session is started — tests inspect conftest module attributes directly.
"""
from __future__ import annotations

import tests.conftest as conftest
from pytest import StashKey
```

New file follows the same pattern — import `tests.conftest` as a module and inspect its attributes:
```python
"""Unit tests for Phase 15 additions to tests/conftest.py.

Covers: COV-07 (pytest_sessionfinish hook), COV-08 (--no-cov detection), COV-09 (coverage link extras).
No real pytest session is started — tests inspect conftest module attributes directly.
"""
from __future__ import annotations

import inspect
import tests.conftest as conftest
```

**Hook existence pattern** from `test_html_report_conftest.py` (lines 82-109):

Tests check: hook exists as callable, has correct `pytest_impl` marker attributes, and source contains expected strings:
```python
class TestPytestConfigure:
    def test_configure_hook_exists(self):
        assert hasattr(conftest, "pytest_configure"), (
            "pytest_configure hook not found in tests/conftest.py"
        )

    def test_configure_hook_is_callable(self):
        assert callable(conftest.pytest_configure), (...)

    def test_configure_hook_has_tryfirst(self):
        hook = conftest.pytest_configure
        opts = getattr(hook, "pytest_impl", {})
        assert opts.get("tryfirst") is True, (...)
```

New file maps the same pattern to `pytest_sessionfinish`:
```python
class TestSessionFinishHook:
    def test_hook_exists(self):
        assert hasattr(conftest, "pytest_sessionfinish")

    def test_hook_is_callable(self):
        assert callable(conftest.pytest_sessionfinish)
```

**Source inspection pattern** from `test_html_report_conftest.py` (lines 128-141):

Uses `inspect.getsource()` to verify hook source contains expected strings without executing the hook:
```python
def test_makereport_source_contains_teardown_branch(self):
    import inspect
    src = inspect.getsource(conftest.pytest_runtest_makereport)
    assert "teardown" in src, (
        "pytest_runtest_makereport must have a 'teardown' branch for extras attachment"
    )
    assert "build_step_table" in src
    assert "html_extras" in src
```

New file uses the same pattern for COV-08 and COV-09:
```python
class TestNoCovDetection:
    def test_sessionfinish_checks_no_cov(self):
        src = inspect.getsource(conftest.pytest_sessionfinish)
        assert "no_cov" in src, (
            "pytest_sessionfinish must check config.option.no_cov (D-11)"
        )

class TestCoverageLinkExtras:
    def test_makereport_source_contains_coverage_link(self):
        src = inspect.getsource(conftest.pytest_runtest_makereport)
        assert "coverage/index.html" in src, (
            "pytest_runtest_makereport must append coverage/index.html link (D-08)"
        )
```

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** Every existing `src/` file and `tests/unit/` test file
**Apply to:** `src/utils/coverage_index.py`, `tests/unit/test_coverage_index.py`, `tests/unit/test_coverage_conftest.py`
```python
from __future__ import annotations
```
This is the first line of every Python file in the project (CLAUDE.md requirement for Python 3.9.13 forward refs).

### HTML string generation with `html.escape()`
**Source:** `src/utils/html_report.py` lines 3, 39, 78-79, 84-85
**Apply to:** `src/utils/coverage_index.py` — all user-derived strings in HTML output
```python
from html import escape

# Wrap every string that comes from external data (file paths, package names, urls):
f'<td><a href="{escape(f["url"])}">{escape(f["rel"])}</a></td>'
f"<summary><b>{escape(pkg)}/ ({pkg_pct}%)</b></summary>"
```

### Fail-open exception handling
**Source:** `src/utils/videos.py` lines 61-76 (`VideoManager.start()` try/except)
**Apply to:** `pytest_sessionfinish` hook body in `tests/conftest.py`
```python
try:
    result = do_thing()
except Exception as exc:
    import warnings
    warnings.warn(f"coverage_index: {exc}")
```
The test session must never fail due to custom index generation errors. Any exception in `build_custom_index()` is caught at the hook level.

### Inline src imports in tests
**Source:** `tests/unit/test_html_report.py` lines 58-60, 109, etc.
**Apply to:** `tests/unit/test_coverage_index.py`, `tests/unit/test_coverage_conftest.py`
```python
class TestFoo:
    def test_something(self):
        from src.utils.coverage_index import build_custom_index
        result = build_custom_index(...)
        assert "..." in result
```
Never import `src.*` at module level in test files — only inside test methods.

### `<details>/<summary>` collapsible HTML
**Source:** `src/utils/html_report.py` lines 45-55 (`build_step_table()`)
**Apply to:** `src/utils/coverage_index.py` — `_render_package()` function
```python
# html_report.py pattern (plain <details>, expands on click):
"<details>"
f"<summary><b>{header}</b></summary>"
...
"</details>"

# coverage_index.py pattern (D-05: <details open>, expanded by default):
"<details open>"
f"<summary><b>{escape(pkg)}/ ({pkg_pct}%)</b> — {len(files)} files, {pkg_stmts} stmts</summary>"
...
"</details>"
```

### Constants block pattern
**Source:** `src/core/constants.py` lines 14-24
**Apply to:** `src/core/constants.py` — the new `COVERAGE_DIR` constant
```python
# [Category comment]
CONSTANT_NAME: str = "reports/subdir"
```
No trailing comma. Type annotation always `: str`. Comment block precedes each group.

### `Path` for file-system operations
**Source:** `tests/conftest.py` lines 4, 47, 53, 75-76
**Apply to:** `tests/conftest.py` (`pytest_sessionfinish`), `src/utils/coverage_index.py`
```python
from pathlib import Path

# Existence check before I/O:
if not Path(".coverage").exists():
    return

# Writing output:
out = Path(COVERAGE_DIR) / "custom_index.html"
out.write_text(html, encoding="utf-8")
```

---

## No Analog Found

All 6 files have analogs. No files lack a codebase match.

The `_cov_factory` injectable dependency pattern in `build_custom_index()` is novel to this project (no other utils use DI for testability), but follows the established Python `unittest.mock` + default-argument injection idiom used in `test_video_manager.py` (lines 5-6: `from unittest.mock import MagicMock, patch`).

---

## Metadata

**Analog search scope:** `src/utils/`, `src/core/`, `tests/unit/`, `tests/conftest.py`, `.coveragerc`
**Files scanned:** 10 (conftest.py, constants.py, .coveragerc, html_report.py, files.py, videos.py, test_html_report.py, test_html_report_conftest.py, test_conftest_hook.py, test_video_manager.py)
**Pattern extraction date:** 2026-05-31
