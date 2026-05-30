# Phase 12: Support Video Capture for Failed Tests - Pattern Map

**Mapped:** 2026-05-30
**Files analyzed:** 9
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/utils/videos.py` | utility | file-I/O + subprocess | `src/utils/screenshots.py` | exact |
| `src/core/constants.py` | config | — | `src/core/constants.py` (self — modify) | self |
| `src/core/config.py` | config | request-response | `src/core/config.py` (self — modify) | self |
| `tests/conftest.py` | test-infrastructure | event-driven | `tests/conftest.py` (self — modify) | self |
| `configs/env.dev.yaml` | config | — | `configs/env.dev.yaml` (self — modify) | self |
| `configs/env.qa.yaml` | config | — | `configs/env.qa.yaml` (self — modify) | self |
| `configs/env.prod.yaml` | config | — | `configs/env.prod.yaml` (self — modify) | self |
| `.gitignore` | config | — | `.gitignore` (self — modify) | self |
| `tests/unit/test_video_manager.py` | test | — | `tests/unit/test_app_config.py` | role-match |

---

## Pattern Assignments

### `src/utils/videos.py` (utility, file-I/O + subprocess)

**Analog:** `src/utils/screenshots.py`

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

New file replaces the selenium import with stdlib subprocess/platform imports and swaps
`SCREENSHOT_*` constants for `VIDEO_*` constants:
```python
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.constants import VIDEO_DATE_FORMAT, VIDEO_DIR
from src.core.logger import get_logger
from src.utils.files import ensure_dir, safe_filename

logger = get_logger("videos")
```

**Core class pattern** (`src/utils/screenshots.py` lines 16–52 — full file):
```python
class ScreenshotManager:
    """Captures screenshots to a timestamped directory."""

    def __init__(self, base_dir: str = SCREENSHOT_DIR) -> None:
        self._base_dir = Path(base_dir)

    def capture(
        self,
        driver: WebDriver,
        name: str,
        subdirectory: str = "",
    ) -> Optional[str]:
        timestamp = datetime.now().strftime(SCREENSHOT_DATE_FORMAT)
        safe_name = safe_filename(name)
        filename = f"{timestamp}_{safe_name}.png"

        target_dir = self._base_dir / subdirectory if subdirectory else self._base_dir
        ensure_dir(target_dir)
        file_path = target_dir / filename

        try:
            driver.save_screenshot(str(file_path))
            logger.info("Screenshot saved: %s", file_path)
            return str(file_path)
        except Exception as exc:
            logger.warning("Failed to capture screenshot '%s': %s", name, exc)
            return None
```

`VideoManager` mirrors this shape: `__init__(base_dir)` + methods that return `Optional[str]`.
Replace `capture()` with `start(name) -> Optional[str]`, `stop() -> None`, `delete(path) -> None`.
Filename construction (`timestamp + safe_filename + extension`) is identical.

**Path construction pattern** (`src/utils/screenshots.py` lines 38–44):
```python
timestamp = datetime.now().strftime(SCREENSHOT_DATE_FORMAT)
safe_name = safe_filename(name)
filename = f"{timestamp}_{safe_name}.png"

target_dir = self._base_dir / subdirectory if subdirectory else self._base_dir
ensure_dir(target_dir)
file_path = target_dir / filename
```

For `VideoManager.start()`, use same pattern with `.mp4` extension and no subdirectory param.

**Error handling pattern** (`src/utils/screenshots.py` lines 46–52):
```python
try:
    driver.save_screenshot(str(file_path))
    logger.info("Screenshot saved: %s", file_path)
    return str(file_path)
except Exception as exc:
    logger.warning("Failed to capture screenshot '%s': %s", name, exc)
    return None
```

`VideoManager.start()` wraps `subprocess.Popen` in the same try/except, catches
`FileNotFoundError` (ffmpeg not on PATH) and logs WARNING, returns `None`.

---

### `src/core/constants.py` (config — modify)

**Analog:** `src/core/constants.py` (self)

**Existing screenshot block to mirror** (`src/core/constants.py` lines 14–16):
```python
# Screenshot
SCREENSHOT_DIR: str = "reports/screenshots"
SCREENSHOT_DATE_FORMAT: str = "%Y%m%d_%H%M%S"
```

**Add after line 16:**
```python
# Video
VIDEO_DIR: str = "reports/videos"
VIDEO_DATE_FORMAT: str = "%Y%m%d_%H%M%S"
```

---

### `src/core/config.py` (config — modify)

**Analog:** `src/core/config.py` (self)

**Import block pattern** (`src/core/config.py` lines 10–20):
```python
from src.core.constants import (
    CONFIGS_DIR,
    DEFAULT_AJAX_IDLE_TIMEOUT,
    DEFAULT_ENV,
    DEFAULT_EXPLICIT_WAIT_TIMEOUT,
    DEFAULT_PAGE_LOAD_TIMEOUT,
    DEFAULT_POLL_FREQUENCY_MS,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    SCREENSHOT_DIR,
)
```

Add `VIDEO_DIR` to this import block:
```python
from src.core.constants import (
    ...
    SCREENSHOT_DIR,
    VIDEO_DIR,
)
```

**`_resolve_bool` usage pattern** (`src/core/config.py` line 38):
```python
self.headless: bool = self._resolve_bool("HEADLESS", "headless", False)
```

**New field to add** after `self.screenshots_dir` line (line 52):
```python
self.record_video: bool = self._resolve_bool("RECORD_VIDEO", "record_video", False)
```

**`_resolve_bool` implementation** (`src/core/config.py` lines 79–81):
```python
def _resolve_bool(self, env_key: str, yaml_key: str, default: bool) -> bool:
    raw = self._resolve(env_key, yaml_key, str(default))
    return raw.lower() in ("true", "1", "yes")
```

No changes to the resolver methods — the new field uses the existing `_resolve_bool` as-is.

---

### `tests/conftest.py` (test-infrastructure — modify)

**Analog:** `tests/conftest.py` (self)

**Existing imports block** (`tests/conftest.py` lines 1–10):
```python
from __future__ import annotations

import os
from typing import Optional

import pytest

from src.core.config import AppConfig
from src.core.logger import configure_logging
```

**Add to imports:**
```python
from pytest import CollectReport, StashKey
```

**Existing function-scoped fixture pattern** (`tests/conftest.py` lines 64–72):
```python
@pytest.fixture(scope="function")
def driver(app_config: AppConfig):
    """Function-scoped WebDriver. Created fresh for each test and quit on teardown."""
    from src.driver.driver_manager import DriverManager
    manager = DriverManager(app_config)
    web_driver = manager.start()
    yield web_driver
    manager.stop()
```

The `video_recorder` fixture uses the same `scope="function"` and the same
`yield`-then-teardown shape. It must declare `driver` as a parameter so it is
function-scoped and runs after the driver is available.

**Three additions to make (in order):**

1. Module-level stash key (add near top of file, after imports):
```python
_phase_report_key: StashKey[dict[str, CollectReport]] = StashKey()
```

2. Hook implementation (add at module level, outside any class):
```python
@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    rep = yield
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep
    return rep
```

3. `video_recorder` fixture (add after the `driver` fixture):
```python
@pytest.fixture(scope="function")
def video_recorder(request, app_config: AppConfig, driver):
    """Start video recording; retain file only on test failure."""
    from src.utils.videos import VideoManager
    from src.core.logger import get_logger

    _log = get_logger("video_recorder")

    manager = VideoManager()
    video_path = manager.start(request.node.name, headless=app_config.headless or not app_config.record_video)
    yield video_path

    # teardown: read pass/fail from stash (populated by pytest_runtest_makereport)
    report = request.node.stash.get(_phase_report_key, {})

    class _Pass:
        failed = False
        skipped = False

    call_report = report.get("call", _Pass())
    setup_report = report.get("setup", _Pass())

    failed = call_report.failed or setup_report.failed

    if failed and video_path:
        _log.info("Video retained (test failed): %s", video_path)
    elif video_path:
        manager.delete(video_path)

    manager.stop()
```

---

### `configs/env.dev.yaml` (config — modify)

**Analog:** `configs/env.dev.yaml` (self)

**Existing bool field pattern** (line 3):
```yaml
headless: false
```

**Add after the existing `headless` line:**
```yaml
record_video: false
```

---

### `configs/env.qa.yaml` (config — modify)

**Analog:** `configs/env.qa.yaml` (self)

Same pattern as `env.dev.yaml` — add `record_video: false` after the `headless` line (line 3).

---

### `configs/env.prod.yaml` (config — modify)

**Analog:** `configs/env.prod.yaml` (self)

Same pattern as `env.dev.yaml` — add `record_video: false` after the `headless` line (line 3).

---

### `.gitignore` (config — modify)

**Analog:** `.gitignore` (self)

**Existing reports block** (`.gitignore` lines 15–19):
```
# Reports / screenshots (keep dir, ignore contents)
reports/screenshots/
reports/*.html
reports/*.xml
```

**Add `reports/videos/` on the line after `reports/screenshots/`:**
```
# Reports / screenshots / videos (keep dirs, ignore contents)
reports/screenshots/
reports/videos/
reports/*.html
reports/*.xml
```

---

### `tests/unit/test_video_manager.py` (test — new)

**Analog:** `tests/unit/test_app_config.py`

**Imports and class structure pattern** (`tests/unit/test_app_config.py` lines 1–17):
```python
"""Unit tests for AppConfig driver path fields — no browser required."""
from __future__ import annotations

import pytest

from src.core.config import AppConfig


class TestAppConfigDriverPaths:
    """driver_path and browser_binary_path resolution from YAML and env vars."""

    def _yaml(self, tmp_path, data: dict):
        """Write a minimal env.test.yaml and return the config dir."""
        import yaml
        f = tmp_path / "env.test.yaml"
        f.write_text(yaml.dump(data), encoding="utf-8")
        return str(tmp_path)
```

New file mirrors: `from __future__ import annotations`, module-level docstring, `import pytest`,
one class per test group, `monkeypatch` and `tmp_path` fixtures for isolation.

**Test group pattern with defaults test** (`tests/unit/test_app_config.py` lines 19–23):
```python
# --- defaults ---

def test_driver_path_defaults_to_none(self, tmp_path):
    config = AppConfig(env="test", config_dir=str(tmp_path))
    assert config.driver_path is None
```

**Test with monkeypatch pattern** (`tests/unit/test_app_config.py` lines 43–47):
```python
def test_driver_path_from_env_var(self, tmp_path, monkeypatch):
    monkeypatch.setenv("DRIVER_PATH", "/tmp/chromedriver")
    config = AppConfig(env="test", config_dir=str(tmp_path))
    assert config.driver_path == "/tmp/chromedriver"
```

For `test_video_manager.py`, use `monkeypatch.setattr("shutil.which", ...)` to simulate
ffmpeg absent/present, and `tmp_path` for temporary video output directories. No real
subprocess or browser needed.

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** Every file in `src/`
**Apply to:** `src/utils/videos.py`, `tests/unit/test_video_manager.py`
```python
from __future__ import annotations
```

### Logger acquisition
**Source:** `src/utils/screenshots.py` line 13
**Apply to:** `src/utils/videos.py`
```python
from src.core.logger import get_logger
logger = get_logger("videos")
```

### `ensure_dir` + `safe_filename` usage
**Source:** `src/utils/screenshots.py` lines 38–44 and `src/utils/files.py`
**Apply to:** `src/utils/videos.py` — call `ensure_dir(self._base_dir)` before `Popen`, use
`safe_filename(name)` for the output filename component.
```python
from src.utils.files import ensure_dir, safe_filename
```

### Optional[str] return type on fallible operations
**Source:** `src/utils/screenshots.py` line 27
**Apply to:** `VideoManager.start()` — return `Optional[str]`; return `None` for all early-exit
guard cases (headless, no ffmpeg, unsupported platform).

### `_resolve_bool` config field pattern
**Source:** `src/core/config.py` lines 38, 79–81
**Apply to:** `src/core/config.py` — new `record_video` field follows this pattern exactly.
```python
self.record_video: bool = self._resolve_bool("RECORD_VIDEO", "record_video", False)
```

---

## No Analog Found

All files have direct analogs in the codebase. No files require falling back to RESEARCH.md
patterns as the sole reference.

---

## Metadata

**Analog search scope:** `src/utils/`, `src/core/`, `tests/unit/`, `tests/conftest.py`,
`configs/`, `.gitignore`
**Files scanned:** 9 existing files read directly
**Pattern extraction date:** 2026-05-30
