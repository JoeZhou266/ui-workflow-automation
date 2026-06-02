---
phase: 18-support-log-file-path-daily-rolling
reviewed: 2026-06-02T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - src/core/constants.py
  - src/core/config.py
  - src/core/logger.py
  - tests/unit/test_logger.py
  - tests/conftest.py
  - configs/env.qa.yaml
  - configs/env.dev.yaml
  - .gitignore
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-06-02T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 18 introduces `log_file_path` config resolution, daily-rolling file logging via `TimedRotatingFileHandler`, constants `LOG_DIR`/`LOG_FILE_NAME`, and a comprehensive test suite (LOG-01 through LOG-12). The core design is sound: the `type(h) is logging.StreamHandler` guard is correct and well-commented, the idempotency model is coherent, and `ensure_dir` handles nested parent creation properly.

Three warnings were found: a silent level-update regression when `configure_logging` is called a second time with a different level, a missing test for the hot-swap-prevention contract (documented in the docstring but not exercised), and a `when="midnight"` vs `fh.when == "MIDNIGHT"` discrepancy between the implementation and test assertion that is currently correct by luck but fragile. Three info items cover an unused import, dead constants, and a stale `.gitignore` pattern.

No security vulnerabilities were found. The `log_file_path` value is passed directly to `TimedRotatingFileHandler` without sanitization, but this is an internal config-only value (not user-supplied input), which is appropriate for this use case.

## Warnings

### WR-01: Level change on re-call silently ignored for existing handlers

**File:** `src/core/logger.py:43-56`

**Issue:** `root.setLevel(numeric_level)` runs on every call (correct), but the `StreamHandler` and `TimedRotatingFileHandler` are only created once and their `.setLevel()` is never updated on subsequent calls. If `configure_logging("DEBUG")` is called after `configure_logging("INFO")`, the root logger accepts DEBUG records but the existing `StreamHandler` still filters at INFO, so DEBUG messages are silently dropped. This contradicts the common expectation that calling `configure_logging("DEBUG")` makes DEBUG messages visible.

**Fix:** Update handler levels when the handler already exists, or update all attached handlers unconditionally after the guard block:

```python
root = logging.getLogger(_FRAMEWORK_LOGGER_NAME)
numeric_level = getattr(logging, level.upper(), logging.INFO)
root.setLevel(numeric_level)

formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

# ... add handlers if not present ...

# Always sync all handler levels to the requested level.
for h in root.handlers:
    h.setLevel(numeric_level)
```

### WR-02: Hot-swap prevention is documented but not tested

**File:** `tests/unit/test_logger.py:99-183`

**Issue:** The `configure_logging` docstring explicitly states: "Calling again with a different log_file_path has no effect (path is not hot-swapped)." This is a meaningful contract — a second call with a different path should not open a second log file. However, no test exercises this scenario. The existing `test_file_handler_idempotent` (LOG-06) only calls with the same path twice. A caller who passes a different path on the second call would silently get two open file handlers writing to two different files — the guard condition `not any(isinstance(h, TimedRotatingFileHandler) ...)` only checks for the presence of *any* `TimedRotatingFileHandler`, not whether the path matches.

**Fix:** Add a test that calls `configure_logging` twice with different paths and asserts exactly one `TimedRotatingFileHandler` is present:

```python
def test_file_handler_not_hot_swapped(self, tmp_path):
    """Calling configure_logging with a second path does not add a second file handler."""
    from src.core.logger import configure_logging

    path1 = str(tmp_path / "first.log")
    path2 = str(tmp_path / "second.log")
    configure_logging("INFO", log_file_path=path1)
    configure_logging("INFO", log_file_path=path2)
    root = logging.getLogger(FRAMEWORK)
    file_handlers = [
        h for h in root.handlers
        if isinstance(h, logging.handlers.TimedRotatingFileHandler)
    ]
    assert len(file_handlers) == 1
    assert file_handlers[0].baseFilename == str(Path(path1).resolve())
```

### WR-03: LOG_DIR and LOG_FILE_NAME constants are defined but never consumed

**File:** `src/core/constants.py:23-24`

**Issue:** `LOG_DIR = "logs"` and `LOG_FILE_NAME = "workflow.log"` are defined in constants but are not imported or referenced anywhere in the source tree other than `tests/unit/test_logger.py` (which only checks their values, not their use). The default log path is never assembled from these constants — `config.py` and `logger.py` both leave `log_file_path` as `None` by default, and callers must supply the full path. This makes the constants effectively inert documentation, which risks them drifting out of sync with actual conventions over time. The `LOG-12` test verifies their values but not their functional role.

**Fix:** Either use the constants to define a default path (if a default is desired):

```python
# In logger.py or config.py
from src.core.constants import LOG_DIR, LOG_FILE_NAME

DEFAULT_LOG_FILE_PATH = str(Path(LOG_DIR) / LOG_FILE_NAME)
```

Or, if no default is desired and these constants serve only as documentation, add a comment making that explicit and ensure the YAML comment examples reference the same path:

```yaml
# log_file_path: logs/workflow.log   # matches LOG_DIR/LOG_FILE_NAME in constants.py
```

## Info

### IN-01: Unused import `os` in test_logger.py

**File:** `tests/unit/test_logger.py:9`

**Issue:** `import os` is present but `os` is never referenced anywhere in the file. This was likely a leftover from a draft that used `os.environ` directly before switching to `monkeypatch.setenv`.

**Fix:** Remove line 9: `import os`

### IN-02: LOG-05 test assertion passes only because stdlib normalises the `when` argument

**File:** `tests/unit/test_logger.py:156`

**Issue:** `logger.py` passes `when="midnight"` (lowercase) to `TimedRotatingFileHandler`, but the test asserts `fh.when == "MIDNIGHT"` (uppercase). This test passes because CPython's `TimedRotatingFileHandler.__init__` calls `self.when = when.upper()`. The test is correct in what it asserts, but the code comment or a note explaining the normalisation would make this less surprising. A reader seeing `when="midnight"` in `logger.py` and `== "MIDNIGHT"` in the test would reasonably wonder whether there is a mismatch.

**Fix:** Add a brief inline comment in `logger.py` at the `when=` argument:

```python
fh = logging.handlers.TimedRotatingFileHandler(
    log_file_path,
    when="midnight",   # stdlib normalises to "MIDNIGHT" internally
    backupCount=30,
    encoding="utf-8",
)
```

### IN-03: Stale `.gitignore` pattern `log/*.log` predates the `logs/` directory convention

**File:** `.gitignore:15`

**Issue:** Line 15 contains `log/*.log`, which matches files inside a directory named `log` (singular). The project uses `LOG_DIR = "logs"` (plural), and the new line 28 (`logs/`) correctly ignores that directory. The `log/*.log` pattern covers a directory name that does not exist in the project and is not referenced by any constant or config. It is harmless but adds noise and could mislead contributors into thinking there is a `log/` directory.

**Fix:** Remove line 15 (`log/*.log`) from `.gitignore` since it is fully superseded by `logs/` on line 28.

---

_Reviewed: 2026-06-02T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
