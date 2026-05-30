---
phase: 12-support-video-capture
plan: "01"
subsystem: video-infrastructure
tags: [video, ffmpeg, subprocess, config, constants, utils]
dependency_graph:
  requires: []
  provides:
    - src/utils/videos.py (VideoManager class)
    - src/core/constants.py (VIDEO_DIR, VIDEO_DATE_FORMAT)
    - src/core/config.py (AppConfig.record_video)
    - configs/env.*.yaml (record_video: false)
  affects:
    - tests/conftest.py (plan 02 will add video_recorder fixture here)
tech_stack:
  added:
    - ffmpeg subprocess management via stdlib subprocess
    - shutil.which for PATH detection
    - platform.system for cross-platform command selection
  patterns:
    - VideoManager mirrors ScreenshotManager interface shape
    - TDD RED/GREEN cycle per task
    - _resolve_bool pattern for AppConfig bool fields
key_files:
  created:
    - src/utils/videos.py
    - tests/unit/test_video_constants_and_config.py
    - tests/unit/test_video_manager.py
  modified:
    - src/core/constants.py
    - src/core/config.py
    - configs/env.dev.yaml
    - configs/env.qa.yaml
    - configs/env.prod.yaml
    - .gitignore
decisions:
  - "VideoManager.stop() uses b'q' stdin signal (not SIGTERM) for graceful MP4 moov atom finalization"
  - "stdout=DEVNULL and stderr=DEVNULL prevent pipe buffer deadlock on ffmpeg verbose output"
  - "Command built as list (never shell=True) — shell injection impossible"
  - "Linux Wayland detection via WAYLAND_DISPLAY env var — log WARNING and return None"
  - "_find_macos_screen_index() parses avfoundation list_devices output, defaults to '1'"
metrics:
  duration: "3m 43s"
  completed: "2026-05-30"
  tasks_completed: 3
  tests_added: 38
  tests_total: 264
---

# Phase 12 Plan 01: Video Infrastructure Summary

## One-Liner

ffmpeg-based VideoManager with headless/PATH/platform guards, AppConfig.record_video bool field via _resolve_bool, and VIDEO_DIR/VIDEO_DATE_FORMAT constants mirroring the ScreenshotManager pattern.

## What Was Built

### src/core/constants.py
Added two constants after the existing `# Screenshot` block:
- `VIDEO_DIR: str = "reports/videos"` — output directory for recordings
- `VIDEO_DATE_FORMAT: str = "%Y%m%d_%H%M%S"` — filename timestamp format

### src/core/config.py
- Added `VIDEO_DIR` to import block from `src.core.constants`
- Added `self.record_video: bool = self._resolve_bool("RECORD_VIDEO", "record_video", False)` after `screenshots_dir`

### src/utils/videos.py (new file)
`VideoManager` class with:
- `start(name, headless=False) -> Optional[str]` — spawns ffmpeg subprocess, returns file path or None
- `stop() -> None` — sends `b"q"` to stdin, `wait(timeout=10)`, `kill()` fallback on TimeoutExpired
- `delete(path) -> None` — removes video file, noop on FileNotFoundError
- `_build_cmd(system) -> Optional[list]` — returns platform-specific ffmpeg command prefix:
  - Darwin: avfoundation with runtime screen index discovery
  - Linux: x11grab with `$DISPLAY`, None if DISPLAY unset or WAYLAND_DISPLAY set
  - Other: None (Windows unsupported)
- Module-level `_find_macos_screen_index()` — parses `ffmpeg -list_devices` output, defaults to "1"

Guards (all return None + WARNING log):
- `headless=True` — no display to capture
- `shutil.which("ffmpeg") is None` — ffmpeg not installed
- Linux without `$DISPLAY` — x11grab requires X server
- Linux with `$WAYLAND_DISPLAY` — x11grab incompatible with Wayland
- Windows — no gdigrab support (out of scope)

### configs/env.*.yaml
Added `record_video: false` immediately after the `headless:` line in all three env configs (dev, qa, prod).

### .gitignore
Added `reports/videos/` exclusion (deviation — see below).

## TDD Gate Compliance

### Task 1 (constants + config)
- RED: commit `b088254` — 8 failing tests for VIDEO_DIR, VIDEO_DATE_FORMAT, record_video
- GREEN: commit `4780fc0` — implementation, all 8 pass

### Task 2 (VideoManager)
- RED: commit `a676f73` — 30 failing tests for full VideoManager interface
- GREEN: commit `f7b1267` — implementation, all 30 pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added reports/videos/ to .gitignore**
- **Found during:** Post-task cleanup review (RESEARCH.md identified this gap)
- **Issue:** `.gitignore` had `reports/screenshots/` but not `reports/videos/`. Without this, video files created during tests would be tracked by git and risk accidental commit.
- **Fix:** Added `reports/videos/` to `.gitignore` after the `reports/screenshots/` line
- **Files modified:** `.gitignore`
- **Commit:** `3a04525`

**2. [Rule 1 - Bug] Fixed test mock setup for stop() TimeoutExpired test**
- **Found during:** Task 2 GREEN phase, test run
- **Issue:** `mock_proc.wait.side_effect = subprocess.TimeoutExpired(...)` caused both `wait(timeout=10)` and bare `wait()` after kill to raise, making the kill path unreachable and the test fail
- **Fix:** Changed to `side_effect = [TimeoutExpired(...), None]` so first call raises and second succeeds
- **Files modified:** `tests/unit/test_video_manager.py`
- **Commit:** Included in `f7b1267`

**3. [Rule 1 - Bug] Fixed test assertion for already-terminated process**
- **Found during:** Task 2 GREEN phase, test run
- **Issue:** `MagicMock(spec=subprocess.Popen)` doesn't expose `stdin` attribute, so `mock_proc.stdin.write.assert_not_called()` raised AttributeError. The code correctly returns early when `proc.poll()` returns non-None, so stdin is never accessed.
- **Fix:** Changed assertion to `assert m._proc is None` and `mock_proc.wait.assert_not_called()`
- **Files modified:** `tests/unit/test_video_manager.py`
- **Commit:** Included in `f7b1267`

## Known Stubs

None. All interfaces are fully implemented.

## Threat Flags

No new security-relevant surface introduced beyond what is documented in the plan's threat model (T-12-01 through T-12-04). All mitigations implemented:
- T-12-02 (DoS via subprocess hang): `wait(timeout=10)` + `kill()` fallback implemented in `stop()`
- T-12-03 (Shell injection): Command is a list literal; `shell=False` (implicit default)

## Self-Check

### Files Exist
- [x] `src/utils/videos.py` — created
- [x] `src/core/constants.py` — VIDEO_DIR and VIDEO_DATE_FORMAT added
- [x] `src/core/config.py` — record_video field added
- [x] `configs/env.dev.yaml` — record_video: false added
- [x] `configs/env.qa.yaml` — record_video: false added
- [x] `configs/env.prod.yaml` — record_video: false added
- [x] `.gitignore` — reports/videos/ added
- [x] `tests/unit/test_video_constants_and_config.py` — created
- [x] `tests/unit/test_video_manager.py` — created

### Test Results
- 264 unit tests pass (226 pre-existing + 38 new)
- No regressions

## Self-Check: PASSED
