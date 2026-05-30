---
phase: 12-support-video-capture
fixed_at: 2026-05-30T18:52:00Z
review_path: .planning/phases/12-support-video-capture/12-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report

**Fixed at:** 2026-05-30T18:52:00Z
**Source review:** .planning/phases/12-support-video-capture/12-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: `delete()` called before `stop()` — ffmpeg writes to unlinked inode on test pass

**Files modified:** `tests/conftest.py`
**Commit:** 1cd10ba
**Applied fix:** Reordered the teardown sequence in `video_recorder` to call `manager.stop()` first (finalize recording), then conditionally call `manager.delete(video_path)` on test pass. Previously, `delete()` was called at line 125 and `stop()` at line 127; now `stop()` is at line 121 and `delete()` follows at line 127.

---

### WR-02: `stop()` does not call `wait()` on `BrokenPipeError`/`OSError` — potential zombie process on Linux

**Files modified:** `src/utils/videos.py`
**Commit:** fc51f8a
**Applied fix:** Replaced the bare `pass` in the `except (BrokenPipeError, OSError)` block with a `self._proc.wait(timeout=5)` call inside a nested try/except. If that wait times out, the process is killed and waited again. This ensures the process is reaped even when it exits unexpectedly before stdin can be written.

---

### WR-03: `_build_cmd` reads `$DISPLAY` from `os.environ` twice

**Files modified:** `src/utils/videos.py`
**Commit:** 22ec86f
**Applied fix:** Replaced `os.environ.get("DISPLAY", ":0.0")` in the Linux return list with the already-validated local variable `display`. The `:0.0` fallback was dead code since the early-return guard at line 134 guarantees `display` is non-empty by the time the return statement is reached.

---

### WR-04: `VideoManager` output directory is not configurable — asymmetry with `ScreenshotManager`

**Files modified:** `src/core/config.py`, `configs/env.dev.yaml`, `configs/env.qa.yaml`, `configs/env.prod.yaml`, `tests/conftest.py`
**Commit:** c422ec9
**Applied fix:** Three-part change:
1. Added `self.videos_dir: str = self._resolve("VIDEOS_DIR", "videos_dir", VIDEO_DIR)` to `AppConfig.__init__()`, following the same `_resolve` pattern as `screenshots_dir`.
2. Added `videos_dir: reports/videos` to all three env YAML files (`env.dev.yaml`, `env.qa.yaml`, `env.prod.yaml`).
3. Updated `video_recorder` fixture in `tests/conftest.py` to instantiate `VideoManager(base_dir=app_config.videos_dir)` instead of `VideoManager()`, making the output directory configurable via YAML and the `VIDEOS_DIR` environment variable.

---

## Post-Fix Verification

Unit test suite result: **284 passed in 0.25s** (no regressions).

Command: `pytest tests/unit/ -q`

---

_Fixed: 2026-05-30T18:52:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
