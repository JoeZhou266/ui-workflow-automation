---
phase: 18-support-log-file-path-daily-rolling
plan: "01"
subsystem: core-logging
tags: [logging, file-handler, daily-rolling, config, unit-tests]
dependency_graph:
  requires: []
  provides: [log-file-path-config, timed-rotating-file-handler, log-constants]
  affects: [src/core/logger.py, src/core/config.py, src/core/constants.py, tests/conftest.py]
tech_stack:
  added: [logging.handlers.TimedRotatingFileHandler]
  patterns: [per-type-idempotency-guard, optional-field-resolution, ensure_dir-before-handler]
key_files:
  created:
    - tests/unit/test_logger.py
  modified:
    - src/core/constants.py
    - src/core/config.py
    - src/core/logger.py
    - configs/env.qa.yaml
    - configs/env.dev.yaml
    - tests/conftest.py
    - .gitignore
decisions:
  - "Per-type idempotency guards (type(h) is logging.StreamHandler for stream, isinstance for file) replace blanket 'if not root.handlers:' to allow both handler types to coexist"
  - "Exact type check (type(h) is logging.StreamHandler) prevents isinstance false-positive since TimedRotatingFileHandler inherits from StreamHandler via FileHandler"
  - "ensure_dir called before TimedRotatingFileHandler construction to auto-create parent directory"
  - "log_file_path field added to AppConfig using existing _resolve_optional pattern (env var LOG_FILE_PATH takes priority over YAML key)"
metrics:
  duration: "~9 minutes"
  completed_date: "2026-06-02"
  tasks_completed: 3
  files_modified: 7
  files_created: 1
---

# Phase 18 Plan 01: Log File Path with Daily Rolling Summary

**One-liner:** TimedRotatingFileHandler added to configure_logging with per-type idempotency guards, midnight rotation, 30-day retention, and AppConfig.log_file_path opt-in field.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add constants, AppConfig field, YAML examples, .gitignore entry | 933531d | src/core/constants.py, src/core/config.py, configs/env.*.yaml, .gitignore |
| 2 | Extend configure_logging with TimedRotatingFileHandler and update conftest.py | 1b8caa2 | src/core/logger.py, tests/conftest.py |
| 3 | Write tests/unit/test_logger.py with 12 tests (LOG-01..LOG-12) | dd23755 | tests/unit/test_logger.py |

## Files Modified

### src/core/constants.py
Added a new `# Log` block after the `# Video` block:
```python
LOG_DIR: str = "logs"
LOG_FILE_NAME: str = "workflow.log"
```

### src/core/config.py
Added `log_file_path` optional field using the existing `_resolve_optional` pattern:
```python
self.log_file_path: Optional[str] = self._resolve_optional("LOG_FILE_PATH", "log_file_path")
```
Env var `LOG_FILE_PATH` takes priority over YAML key `log_file_path`. Defaults to `None` when neither is set.

### src/core/logger.py
Full replacement of `configure_logging`:
- Added imports: `import logging.handlers`, `from pathlib import Path`, `from src.utils.files import ensure_dir`
- Replaced blanket `if not root.handlers:` guard with two independent per-type guards
- StreamHandler guard: `if not any(type(h) is logging.StreamHandler for h in root.handlers)` — exact type check to avoid false-positive from `TimedRotatingFileHandler` (which inherits from `StreamHandler`)
- FileHandler guard: `if log_file_path and not any(isinstance(h, logging.handlers.TimedRotatingFileHandler) for h in root.handlers)`
- `TimedRotatingFileHandler` parameters: `when="midnight"`, `backupCount=30`, `encoding="utf-8"`
- `ensure_dir(Path(log_file_path).parent)` called before handler construction

### configs/env.qa.yaml + configs/env.dev.yaml
Added commented example line after the `browser_binary_path` comment:
```yaml
# log_file_path:        # e.g. logs/workflow.log             (leave commented to disable file logging)
```

### tests/conftest.py
Updated `configure_logging` call site from:
```python
configure_logging(config.log_level)
```
to:
```python
configure_logging(config.log_level, config.log_file_path)
```

### .gitignore
Added `logs/` entry under a new comment block:
```
# Log files (daily-rolling output — runtime artefacts, not committed)
logs/
```

### tests/unit/test_logger.py (NEW)
Created with 3 classes and 12 tests covering LOG-01 through LOG-12:
- `TestLogConstants` (1 test — LOG-12): verifies `LOG_DIR == "logs"` and `LOG_FILE_NAME == "workflow.log"` importable
- `TestLogFilePathConfig` (4 tests — LOG-08..LOG-11): defaults to None, reads from YAML, reads from env var, env var beats YAML
- `TestConfigureLogging` (7 tests — LOG-01..LOG-07): stream handler added, stream handler idempotent, no file handler when path=None, file handler added when path set, rotation params (MIDNIGHT/30/utf-8), file handler idempotent, parent dir auto-created
- Module-level `reset_framework_logger` fixture with `autouse=True` clears handlers before/after each test

## Test Results

- New tests: 12 passed, 0 failed (tests/unit/test_logger.py)
- Full unit suite: **394 passed, 0 failed** (baseline 382 + 12 new)
- LOG-01 through LOG-12: all green

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all log configuration is wired to real AppConfig fields and live handler objects.

## Threat Flags

None — no new network endpoints or trust boundary surface introduced. The `log_file_path` field follows the established operator-trusted config pattern already in use for `driver_path` and `browser_binary_path`.

## Self-Check

- [x] src/core/constants.py — LOG_DIR and LOG_FILE_NAME constants present and importable
- [x] src/core/config.py — log_file_path field present
- [x] src/core/logger.py — configure_logging has correct signature and implementation
- [x] configs/env.qa.yaml — commented log_file_path example line present
- [x] configs/env.dev.yaml — commented log_file_path example line present
- [x] tests/conftest.py — configure_logging call passes log_file_path
- [x] .gitignore — logs/ entry present at line 28
- [x] tests/unit/test_logger.py — 12 tests all pass
- [x] Full unit suite — 394 tests green, 0 regressions
- [x] Old blanket guard `if not root.handlers:` removed from logger.py
- [x] Task commits: 933531d, 1b8caa2, dd23755
