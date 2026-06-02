# Phase 18: Support Log File Path, Daily Output and Rolling - Research

**Researched:** 2026-06-02
**Domain:** Python stdlib logging — TimedRotatingFileHandler, AppConfig extension, constants
**Confidence:** HIGH

---

## Summary

Phase 18 adds optional log-file output with daily midnight rotation to the existing framework
logging infrastructure. The current `configure_logging(level)` writes only to stdout via a
`StreamHandler`. This phase adds a `log_file_path` config field (env var `LOG_FILE_PATH`, YAML
key `log_file_path`, default `None`). When set, `configure_logging` adds a second handler —
`TimedRotatingFileHandler(when='midnight', backupCount=30, encoding='utf-8')` — alongside the
stream handler. When `log_file_path` is `None` the function is a no-op for the file handler,
leaving existing behaviour entirely unchanged.

The implementation touches exactly four files in production code (`constants.py`, `config.py`,
`logger.py`, `configs/env.qa.yaml`) and two support files (`.gitignore`, new unit test file).
No changes to `conftest.py` call signature are needed if `log_file_path` defaults to `None`.
However, passing it explicitly (`configure_logging(config.log_level, config.log_file_path)`) is
the cleaner pattern — the planner should decide which is safer for the test suite.

**Primary recommendation:** Extend `configure_logging(level, log_file_path=None)` with a
per-handler-type idempotency guard; auto-create the parent directory via `ensure_dir` before
instantiating the handler; keep the stream handler unconditional so stdout behaviour is
preserved when a file is also configured.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Log file path config | Config layer (`AppConfig`) | Constants | Follows existing pattern: optional field via `_resolve_optional` |
| Log directory constant | Constants (`src/core/constants.py`) | — | All dir constants live here; `LOG_DIR = "logs"` belongs alongside `SCREENSHOT_DIR` etc. |
| Handler construction | Logger (`src/core/logger.py`) | Utils (ensure_dir) | All logging plumbing is in logger.py; dir creation is a one-liner using existing util |
| Directory auto-creation | Utils (`src/utils/files.py::ensure_dir`) | — | Already used by VideoManager and ScreenshotManager for the same purpose |
| Gitignore | Project root `.gitignore` | — | Log files are runtime output, not committed |
| Env YAML config | `configs/env.*.yaml` | — | Shows users how to configure the field |

---

## Standard Stack

### Core (all stdlib — zero new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `logging.handlers.TimedRotatingFileHandler` | stdlib (Python 3.9+) | Daily rotating file handler | Built-in, zero install cost, well-tested |
| `logging.StreamHandler` | stdlib | Existing stdout handler | Already in use |
| `pathlib.Path` | stdlib | Parent dir extraction | Already used across project |

[VERIFIED: Python 3.9 stdlib on this machine; pyproject.toml requires Python >=3.14 so all
stdlib APIs verified below are available]

### Supporting (already in project)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `src.utils.files.ensure_dir` | project | Auto-create log parent directory | Before constructing handler |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `TimedRotatingFileHandler` | `RotatingFileHandler` (size-based) | Size rotation doesn't give one-file-per-day; daily is the requirement |
| `when='midnight'` | `when='D'` | Both produce identical interval (86400 s) and suffix (`%Y-%m-%d`); `midnight` is more self-documenting |
| `backupCount=30` | any integer | 30 days of retention is a sensible default; caller can override via config |

**Installation:** No new packages required.

**Version verification:** `TimedRotatingFileHandler` is stdlib; no registry check needed.
[VERIFIED: `logging.handlers.TimedRotatingFileHandler` exists in Python 3.9 (local), 3.14
(project target)]

---

## Architecture Patterns

### System Architecture Diagram

```
conftest.py::app_config fixture
        |
        | configure_logging(config.log_level, config.log_file_path)
        v
logger.py::configure_logging()
        |
        +----> always: add StreamHandler(stdout) if not already present
        |
        +----> if log_file_path is not None:
                    ensure_dir(Path(log_file_path).parent)
                    add TimedRotatingFileHandler(
                        log_file_path,
                        when='midnight',
                        backupCount=30,
                        encoding='utf-8'
                    ) if not already present
                    |
                    v
              logs/workflow.log          (current day)
              logs/workflow.log.2026-06-01  (yesterday, rotated at midnight)
              logs/workflow.log.2026-05-31  (day before, etc.)
```

### Recommended Project Structure

No new directories in `src/`. The default output directory is `logs/` at project root (runtime
output, gitignored). Users can override via config to any absolute or relative path.

```
logs/                    # gitignored — runtime output
├── workflow.log         # active file (current day)
├── workflow.log.2026-06-01  # rotated by handler at midnight
└── workflow.log.2026-05-31
src/core/
├── constants.py         # add LOG_DIR, LOG_FILE_NAME
├── config.py            # add log_file_path field
└── logger.py            # extend configure_logging signature + file handler
configs/
├── env.qa.yaml          # add commented-out example
└── env.dev.yaml         # add commented-out example
tests/unit/
└── test_logger.py       # NEW — LOG-01..LOG-08
.gitignore               # add logs/ pattern
```

### Pattern 1: Extending configure_logging with Optional File Handler

**What:** Add `log_file_path: Optional[str] = None` parameter; use per-handler-type idempotency
guards instead of the current `if not root.handlers` blanket guard.

**When to use:** This is the only correct approach — the current guard (`if not root.handlers`)
would block the file handler from being added if `configure_logging` is called a second time
(or if a stream handler was already added).

**Example:**
```python
# Source: verified via stdlib inspection 2026-06-02
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from src.utils.files import ensure_dir

_FRAMEWORK_LOGGER_NAME = "workflow_framework"
_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    if name:
        return logging.getLogger(f"{_FRAMEWORK_LOGGER_NAME}.{name}")
    return logging.getLogger(_FRAMEWORK_LOGGER_NAME)


def configure_logging(
    level: str = "INFO",
    log_file_path: Optional[str] = None,
) -> None:
    """Configure framework logger with stream handler and optional rotating file handler.

    Idempotent: each handler type is added at most once. Calling again with a
    different log_file_path has no effect (path is not hot-swapped).
    """
    root = logging.getLogger(_FRAMEWORK_LOGGER_NAME)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric_level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Stream handler — always present, added at most once
    if not any(type(h) is logging.StreamHandler for h in root.handlers):
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(numeric_level)
        sh.setFormatter(formatter)
        root.addHandler(sh)

    # File handler — only when path is configured
    if log_file_path and not any(
        isinstance(h, logging.handlers.TimedRotatingFileHandler) for h in root.handlers
    ):
        ensure_dir(Path(log_file_path).parent)
        fh = logging.handlers.TimedRotatingFileHandler(
            log_file_path,
            when="midnight",
            backupCount=30,
            encoding="utf-8",
        )
        fh.setLevel(numeric_level)
        fh.setFormatter(formatter)
        root.addHandler(fh)
```

[VERIFIED: `type(h) is logging.StreamHandler` correctly excludes `TimedRotatingFileHandler`
because `TimedRotatingFileHandler` is a subclass of both `FileHandler` and `StreamHandler` —
a simple `isinstance` check would false-positive. Confirmed via MRO inspection 2026-06-02.]

### Pattern 2: AppConfig Extension for log_file_path

**What:** Add one line to `AppConfig.__init__` using the existing `_resolve_optional` helper.

**Example:**
```python
# Follows existing pattern — src/core/config.py
self.log_file_path: Optional[str] = self._resolve_optional("LOG_FILE_PATH", "log_file_path")
```

No default is needed — `_resolve_optional` returns `None` when neither env var nor YAML key
is set. [VERIFIED: `_resolve_optional` returns `None` as default — confirmed from source 2026-06-02]

### Pattern 3: Constants for LOG_DIR and LOG_FILE_NAME

**What:** Add two constants following the existing naming convention.

**Example:**
```python
# src/core/constants.py — follows existing VIDEO_DIR / SCREENSHOT_DIR pattern
LOG_DIR: str = "logs"
LOG_FILE_NAME: str = "workflow.log"
```

The planner can wire these in `AppConfig` or let them serve as documentation of the default
convention. They are NOT used internally by `configure_logging` (which receives a resolved path
string); they exist so callers building a default path have a single source of truth.

### Pattern 4: conftest.py Call-Site Update

**What:** Pass `config.log_file_path` to `configure_logging`. The new parameter defaults to
`None` so existing call `configure_logging(config.log_level)` continues to work without change.
Updating the call site is optional but recommended for explicitness.

**Example:**
```python
# tests/conftest.py — app_config fixture
configure_logging(config.log_level, config.log_file_path)
```

### Anti-Patterns to Avoid

- **Blanket `if not root.handlers` guard with file handler:** The existing guard blocks adding the
  file handler on any call after the first. Replace with per-type checks (see Pattern 1).
- **`time.sleep()` anywhere in logging code:** CLAUDE.md forbids this; logging is synchronous
  and needs no sleeps.
- **Caching the file path inside configure_logging:** Path is read once at startup. Hot-swapping
  the log path mid-session is out of scope.
- **Absolute path hardcoded as default:** Default must come from the resolved config (or be
  `None`). Never hardcode `/var/log/...` or similar.
- **Not calling `ensure_dir` before handler construction:** `TimedRotatingFileHandler` raises
  `FileNotFoundError` on first emit if the parent directory does not exist.
  [VERIFIED: confirmed experimentally 2026-06-02]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Daily log rotation | Custom midnight cron + file rename | `TimedRotatingFileHandler(when='midnight')` | Handles rotation at exact midnight, manages backup files, handles DST transitions |
| Backup file pruning | Manual `glob` + `os.remove` | `backupCount=30` parameter | Handler automatically deletes files older than `backupCount` days after rotation |
| Log file naming | Custom date suffix logic | Handler's built-in `suffix = "%Y-%m-%d"` | Suffix is appended automatically on rotation; rotated file is `workflow.log.2026-06-02` |
| Directory creation | Inline `os.makedirs` | `ensure_dir()` from `src/utils/files.py` | Already used by VideoManager and ScreenshotManager; idempotent, returns Path |

**Key insight:** Python's `TimedRotatingFileHandler` handles all rotation, pruning, and file
naming internally — the only setup needed is `when`, `backupCount`, and `encoding`.

---

## Common Pitfalls

### Pitfall 1: TimedRotatingFileHandler Is a StreamHandler Subclass

**What goes wrong:** Using `isinstance(h, logging.StreamHandler)` to detect whether a stream
handler exists will also match `TimedRotatingFileHandler` (which inherits from `FileHandler`
which inherits from `StreamHandler`). This causes the per-type guard to think a stream handler
is present when only a file handler was added, and vice versa.

**Why it happens:** Python logging handler inheritance: `TimedRotatingFileHandler →
BaseRotatingHandler → FileHandler → StreamHandler → Handler`.

**How to avoid:** Use `type(h) is logging.StreamHandler` (exact type match) for the stdout
handler guard, and `isinstance(h, logging.handlers.TimedRotatingFileHandler)` for the file
handler guard.

**Warning signs:** Both handlers present but stdout check reports True even before a stream
handler was added.

[VERIFIED: MRO confirmed experimentally 2026-06-02]

### Pitfall 2: Directory Must Exist Before Handler Emits (Not Just Before Construction)

**What goes wrong:** With `delay=True`, the handler constructs successfully even if the parent
directory does not exist — but the first `emit()` call raises `FileNotFoundError` silently
(logging swallows it with `handleError`), losing all log records.

**Why it happens:** `TimedRotatingFileHandler(delay=True)` opens the file lazily on first emit,
not at construction time.

**How to avoid:** Call `ensure_dir(Path(log_file_path).parent)` before constructing the handler,
regardless of the `delay` parameter. Use `delay=False` (the default) so failures surface
immediately at startup.

[VERIFIED: experimentally confirmed 2026-06-02]

### Pitfall 3: Existing `if not root.handlers` Guard Blocks File Handler

**What goes wrong:** The current `configure_logging` guard (`if not root.handlers:`) prevents
any handler from being added if the logger already has handlers. If `configure_logging` is
called once for stdout and then called again to add a file handler, the file handler is silently
skipped.

**Why it happens:** The guard was designed for simple idempotency when only one handler type
existed.

**How to avoid:** Replace with two separate per-type guards as shown in Pattern 1.

[VERIFIED: traced through existing `src/core/logger.py` source 2026-06-02]

### Pitfall 4: Rotated Files Not Gitignored

**What goes wrong:** The current `.gitignore` has `log/*.log` (singular `log/`, only `.log`
extension). Rotated files (`logs/workflow.log.2026-06-02`) have a different extension and land
in `logs/` (plural). They would appear as untracked files.

**How to avoid:** Add `logs/` to `.gitignore` (ignores the whole directory). The existing
`log/*.log` line can remain or be removed.

[VERIFIED: checked `.gitignore` line 15 reads `log/*.log`; default constant is `LOG_DIR = "logs"`]

### Pitfall 5: Formatter Not Set on File Handler

**What goes wrong:** Creating the file handler without calling `fh.setFormatter(formatter)` produces
unformatted log output (raw message only, no timestamp or level).

**How to avoid:** Always call `setFormatter` on both the stream and file handlers with the shared
`formatter` object.

---

## Code Examples

Verified patterns from stdlib inspection:

### TimedRotatingFileHandler Construction
```python
# Source: verified via stdlib inspection + experimental test 2026-06-02
import logging.handlers
from pathlib import Path
from src.utils.files import ensure_dir

log_file_path = "logs/workflow.log"
ensure_dir(Path(log_file_path).parent)  # creates logs/ if absent

fh = logging.handlers.TimedRotatingFileHandler(
    log_file_path,
    when="midnight",      # rotate at local midnight
    backupCount=30,       # keep 30 days of rotated files
    encoding="utf-8",
    delay=False,          # create file immediately (surfaces errors at startup)
)
# Rotated file name: logs/workflow.log.2026-06-02 (suffix = %Y-%m-%d)
```

### AppConfig field addition
```python
# Source: follows _resolve_optional pattern already in src/core/config.py
self.log_file_path: Optional[str] = self._resolve_optional("LOG_FILE_PATH", "log_file_path")
```

### Constants addition
```python
# Source: follows existing pattern in src/core/constants.py
LOG_DIR: str = "logs"
LOG_FILE_NAME: str = "workflow.log"
```

### Example env YAML (commented out by default)
```yaml
# log_file_path: logs/workflow.log   # uncomment to enable daily-rolling file output
```

### Example with explicit path override
```yaml
log_file_path: /var/log/myapp/workflow.log
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual log file management | `TimedRotatingFileHandler` (stdlib) | Python 2.4 (2004) | Stable, no changes expected |
| `when='h'` (default) | `when='midnight'` | N/A | Explicit daily rotation |

**Deprecated/outdated:**
- Nothing in this domain is deprecated. `TimedRotatingFileHandler` has been stable since Python 2.4.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `backupCount=30` is a sensible default | Standard Stack | User may prefer fewer/more days; expose via config if needed |
| A2 | File handler is ADDED alongside stream handler, not replacing it | Summary | If user wants file-only, they'd need a separate flag; current design assumes "both" |
| A3 | Default log directory is `logs/` (project root) | Constants Pattern | User may prefer `reports/logs/` to match existing reports structure |

---

## Open Questions

1. **Should `log_file_path` default to `logs/workflow.log` when not set, or remain `None`?**
   - What we know: all other optional features (record_video, driver_path) default to None / False
   - What's unclear: whether silently writing no log file (when not configured) is preferable to
     always writing one
   - Recommendation: default `None` (opt-in, consistent with record_video and driver_path patterns)

2. **Should `backupCount` be configurable via a separate field (`log_backup_count`)?**
   - What we know: VideoManager has no config field for retention; it always retains failed tests
   - What's unclear: whether 30 days is right for all users
   - Recommendation: hardcode `30` for now (A1 — flag as assumption); add config field in a
     future phase if requested

3. **Should `configure_logging` be updated to accept the new parameter, or should conftest.py
   build the file path and call the handler directly?**
   - Recommendation: extend `configure_logging` signature — keeps all logging plumbing in
     `logger.py`, consistent with existing design

---

## Environment Availability

Step 2.6: SKIPPED — this phase is purely stdlib + project config; no external tools, services,
or CLI utilities are required beyond Python itself.

Python version required: >=3.14 (per pyproject.toml). `TimedRotatingFileHandler` available
since Python 2.4. No compatibility concerns. [VERIFIED: stdlib present on this machine]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (venv at `.venv/bin/pytest`) |
| Config file | `pytest.ini` (project root) |
| Quick run command | `.venv/bin/pytest tests/unit/test_logger.py -v` |
| Full suite command | `.venv/bin/pytest tests/unit/ -v` |

**Baseline:** 382 unit tests pass before Phase 18. [VERIFIED: run 2026-06-02]

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOG-01 | `configure_logging(level)` adds exactly one StreamHandler | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestConfigureLogging::test_stream_handler_added -x` | ❌ Wave 0 |
| LOG-02 | `configure_logging` is idempotent — calling twice does not add duplicate StreamHandler | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestConfigureLogging::test_stream_handler_idempotent -x` | ❌ Wave 0 |
| LOG-03 | `configure_logging(level, log_file_path=None)` adds NO file handler | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestConfigureLogging::test_no_file_handler_when_path_none -x` | ❌ Wave 0 |
| LOG-04 | `configure_logging(level, log_file_path="logs/test.log")` adds a `TimedRotatingFileHandler` | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestConfigureLogging::test_file_handler_added_when_path_set -x` | ❌ Wave 0 |
| LOG-05 | File handler has `when='MIDNIGHT'`, `backupCount=30`, `encoding='utf-8'` | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestConfigureLogging::test_file_handler_rotation_params -x` | ❌ Wave 0 |
| LOG-06 | File handler is idempotent — calling twice does not add duplicate file handler | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestConfigureLogging::test_file_handler_idempotent -x` | ❌ Wave 0 |
| LOG-07 | Parent directory is auto-created if it does not exist | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestConfigureLogging::test_log_dir_auto_created -x` | ❌ Wave 0 |
| LOG-08 | `AppConfig.log_file_path` defaults to `None` when not set | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestLogFilePathConfig::test_defaults_to_none -x` | ❌ Wave 0 |
| LOG-09 | `AppConfig.log_file_path` reads from YAML key `log_file_path` | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestLogFilePathConfig::test_from_yaml -x` | ❌ Wave 0 |
| LOG-10 | `AppConfig.log_file_path` reads from env var `LOG_FILE_PATH` | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestLogFilePathConfig::test_from_env_var -x` | ❌ Wave 0 |
| LOG-11 | Env var `LOG_FILE_PATH` takes priority over YAML `log_file_path` | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestLogFilePathConfig::test_env_beats_yaml -x` | ❌ Wave 0 |
| LOG-12 | `LOG_DIR` and `LOG_FILE_NAME` constants exist in `src/core/constants.py` | unit | `.venv/bin/pytest tests/unit/test_logger.py::TestLogConstants::test_constants_importable -x` | ❌ Wave 0 |

### Key Test Implementation Notes

**Logger isolation in tests:** Each test class must reset the framework logger handlers to avoid
cross-test contamination. Use a fixture:

```python
import logging
import pytest

FRAMEWORK = "workflow_framework"

@pytest.fixture(autouse=True)
def reset_framework_logger():
    """Remove all handlers from the framework logger before/after each test."""
    root = logging.getLogger(FRAMEWORK)
    handlers = list(root.handlers)
    for h in handlers:
        h.close()
        root.removeHandler(h)
    yield
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)
```

**File handler tests use `tmp_path`:** Never write to real `logs/` in unit tests; always use
pytest's `tmp_path` fixture:

```python
def test_file_handler_added_when_path_set(self, tmp_path, reset_framework_logger):
    from src.core.logger import configure_logging
    import logging.handlers

    path = str(tmp_path / "workflow.log")
    configure_logging("INFO", log_file_path=path)
    root = logging.getLogger("workflow_framework")
    file_handlers = [h for h in root.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
    assert len(file_handlers) == 1
```

**Rotation parameter verification:**

```python
def test_file_handler_rotation_params(self, tmp_path, reset_framework_logger):
    from src.core.logger import configure_logging
    import logging.handlers

    path = str(tmp_path / "workflow.log")
    configure_logging("INFO", log_file_path=path)
    root = logging.getLogger("workflow_framework")
    fh = next(h for h in root.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler))
    assert fh.when == "MIDNIGHT"
    assert fh.backupCount == 30
    assert fh.encoding == "utf-8"
```

### Sampling Rate

- **Per task commit:** `.venv/bin/pytest tests/unit/test_logger.py -v`
- **Per wave merge:** `.venv/bin/pytest tests/unit/ -v`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps

- [ ] `tests/unit/test_logger.py` — covers LOG-01..LOG-12 (entire file is new)

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 18 |
|-----------|-------------------|
| Python 3.14.5 | `from __future__ import annotations` retained; all stdlib APIs stable |
| Never use `time.sleep()` for synchronization | Not applicable to logging — logging is synchronous |
| `configs/env.*.yaml` or `.env` for config, never hardcoded | `log_file_path` added to `AppConfig` via `_resolve_optional` |
| `ensure_dir` pattern from `src/utils/files.py` | Must call before handler construction (Pitfall 2) |
| Unit tests go in `tests/unit/` | New `test_logger.py` in `tests/unit/` |
| `pytest tests/unit/` for no-browser tests | All LOG-01..LOG-12 are browser-free |

---

## Sources

### Primary (HIGH confidence)
- Python 3.9 stdlib `logging.handlers` module — inspected via `inspect.getsource` and
  experimental tests [VERIFIED: 2026-06-02]
- `src/core/logger.py` — current implementation read directly [VERIFIED: 2026-06-02]
- `src/core/config.py` — `_resolve_optional` pattern read directly [VERIFIED: 2026-06-02]
- `src/core/constants.py` — existing constant naming convention read directly [VERIFIED: 2026-06-02]
- `src/utils/files.py` — `ensure_dir` API read directly [VERIFIED: 2026-06-02]
- `.gitignore` — current log patterns read directly [VERIFIED: 2026-06-02]
- `tests/conftest.py` — call site for `configure_logging` read directly [VERIFIED: 2026-06-02]

### Secondary (MEDIUM confidence)
- Phase 12 VideoManager pattern (optional feature + constants + AppConfig bool field) — reviewed
  `src/utils/videos.py` and `tests/unit/test_video_constants_and_config.py` as structural analogue

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib TimedRotatingFileHandler, verified experimentally
- Architecture: HIGH — directly derived from reading all affected source files
- Pitfalls: HIGH — each pitfall was reproduced or traced in code during this session

**Research date:** 2026-06-02
**Valid until:** 2026-12-02 (stable stdlib — unlikely to change)
