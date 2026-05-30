---
phase: 12-support-video-capture
reviewed: 2026-05-30T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - .gitignore
  - configs/env.dev.yaml
  - configs/env.prod.yaml
  - configs/env.qa.yaml
  - src/core/config.py
  - src/core/constants.py
  - src/utils/videos.py
  - tests/conftest.py
  - tests/unit/test_conftest_hook.py
  - tests/unit/test_conftest_video_recorder.py
  - tests/unit/test_video_constants_and_config.py
  - tests/unit/test_video_manager.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-05-30
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

This phase introduces `VideoManager` (screen recording via ffmpeg), the `video_recorder` fixture, a `pytest_runtest_makereport` hook, `record_video` config, and associated constants. The core design is sound: subprocess lifecycle is guarded with explicit checks, the hook correctly uses `wrapper=True` (not the deprecated `hookwrapper=True`), and the test suite is thorough. No critical security or correctness issues were found.

Four warnings require attention before merging:

1. The `stop()` teardown ordering in `conftest.py` calls `delete()` before `stop()`, leaving ffmpeg running while the file is unlinked.
2. The `BrokenPipeError`/`OSError` exception branch in `VideoManager.stop()` exits without calling `wait()`, leaving a zombie process on Linux.
3. The `_build_cmd` Linux path reads `$DISPLAY` from `os.environ` a second time instead of reusing the already-validated local variable.
4. `AppConfig` exposes `screenshots_dir` as a configurable field but `VideoManager` ignores `app_config` entirely for its output directory, creating a configuration asymmetry.

---

## Warnings

### WR-01: `delete()` called before `stop()` — ffmpeg writes to unlinked inode on test pass

**File:** `tests/conftest.py:121-127`

**Issue:** In the `video_recorder` teardown, `manager.delete(video_path)` is invoked on the pass path before `manager.stop()`. On POSIX systems the file is unlinked while ffmpeg is still writing to it; the process holds the open file descriptor so disk space is not reclaimed until `stop()` completes. On a slow or stalled `stop()` (up to the 10-second timeout), the test suite holds consumed disk space invisibly. More importantly, the semantic intent — "record, then discard" — is violated: the correct sequence is to stop recording first, then delete the now-complete file.

**Fix:**
```python
# Correct ordering in video_recorder teardown:
manager.stop()          # finalize the recording first

if video_path:
    if test_failed:
        _log.info("Video retained (test failed): %s", video_path)
    else:
        manager.delete(video_path)   # delete after ffmpeg has exited cleanly
```

---

### WR-02: `stop()` does not call `wait()` on `BrokenPipeError`/`OSError` — potential zombie process on Linux

**File:** `src/utils/videos.py:90-91`

**Issue:** When `stdin.write(b"q")`, `stdin.flush()`, or `stdin.close()` raise `BrokenPipeError` or `OSError`, the exception is silently caught and the `finally` block sets `self._proc = None` without ever calling `self._proc.wait()`. The process that caused the broken pipe likely exited on its own, but without `wait()` the OS cannot reap the zombie entry from the process table on Linux. This holds a slot in the process table per test until the Python process itself exits.

**Fix:**
```python
except (BrokenPipeError, OSError):
    # Process died before we could write; reap it to avoid zombie.
    try:
        self._proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        self._proc.kill()
        self._proc.wait()
```

---

### WR-03: `_build_cmd` reads `$DISPLAY` from `os.environ` twice

**File:** `src/utils/videos.py:133, 152`

**Issue:** The Linux branch assigns `display = os.environ.get("DISPLAY")` at line 133, checks it for emptiness at line 135, then discards it and calls `os.environ.get("DISPLAY", ":0.0")` again at line 152. By line 152 `display` is guaranteed non-empty (the early return guards against it), so the fallback `":0.0"` is dead code and the double read is a maintenance footgun — a future refactor could change line 133 without updating line 152.

**Fix:**
```python
if system == "Linux":
    display = os.environ.get("DISPLAY")
    if not display:
        logger.warning(
            "No DISPLAY env var — video recording disabled (Wayland or no X server)"
        )
        return None
    wayland = os.environ.get("WAYLAND_DISPLAY")
    if wayland:
        logger.warning(
            "Wayland detected ($WAYLAND_DISPLAY=%s) — x11grab not supported; "
            "video recording disabled",
            wayland,
        )
        return None
    return [
        "ffmpeg", "-y",
        "-f", "x11grab",
        "-framerate", "15",
        "-video_size", "1920x1080",
        "-i", display,          # reuse already-validated local variable
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
    ]
```

---

### WR-04: `VideoManager` output directory is not configurable — asymmetry with `ScreenshotManager`

**File:** `tests/conftest.py:104` and `src/core/config.py`

**Issue:** `ScreenshotManager` receives its output directory from `app_config.screenshots_dir`, which is configurable via `env.*.yaml` and the `SCREENSHOTS_DIR` environment variable. `VideoManager()` in the `video_recorder` fixture is constructed with no arguments, hardcoding `VIDEO_DIR = "reports/videos"`. There is no `videos_dir` field in `AppConfig` and no corresponding YAML key in any env config. Callers cannot redirect video output (e.g., to a CI artifact directory) without modifying source code. This breaks the configuration parity promised by the architecture.

**Fix — two-part:**

1. Add `videos_dir` to `AppConfig` (`src/core/config.py`):
```python
self.videos_dir: str = self._resolve("VIDEOS_DIR", "videos_dir", VIDEO_DIR)
```

2. Pass it to `VideoManager` in the fixture (`tests/conftest.py`):
```python
manager = VideoManager(base_dir=app_config.videos_dir)
```

Also add `videos_dir` to each `env.*.yaml` if a non-default value is desired.

---

## Info

### IN-01: `test_missing_stash_handled_gracefully` comment contradicts missing assertion

**File:** `tests/unit/test_conftest_video_recorder.py:232-233`

**Issue:** The inline comment at line 232 states "With empty stash, _Pass sentinel treats as passed => delete called", but the test does not assert `mock_manager.delete.assert_called_once_with(video_path)`. Only `stop()` is asserted. The comment creates a false impression that the delete behavior is verified.

**Fix:** Add the missing assertion, or remove the comment if the intent is only to verify no exception is raised:
```python
# With empty stash the _Pass sentinel is used -> test treated as passed -> delete called
mock_manager.delete.assert_called_once_with(video_path)
mock_manager.stop.assert_called_once()
```

---

### IN-02: Missing test case for `record_video=False` → `headless=True` forwarded to `start()`

**File:** `tests/unit/test_conftest_video_recorder.py`

**Issue:** `test_start_passes_headless_when_headless_true` covers `headless=True` with `record_video=True`. The fixture also suppresses recording when `record_video=False` (via `headless = app_config.headless or not app_config.record_video`). There is no test asserting that `record_video=False` with `headless=False` results in `start(headless=True)`.

**Fix:** Add a complementary test:
```python
def test_start_passes_headless_when_record_video_false(self, mock_app_config, mock_driver):
    mock_app_config.headless = False
    mock_app_config.record_video = False
    request = self._make_request(call_failed=False)

    with patch("src.utils.videos.VideoManager") as MockVideoManagerClass:
        mock_manager = MagicMock()
        MockVideoManagerClass.return_value = mock_manager
        mock_manager.start.return_value = None

        gen = self._call_fixture(request, mock_app_config, mock_driver)
        next(gen)
        try:
            next(gen)
        except StopIteration:
            pass

        _, kwargs = mock_manager.start.call_args
        assert kwargs.get("headless") is True
```

---

### IN-03: Misleading docstring on `VideoManager` — does not mirror `ScreenshotManager`

**File:** `src/utils/videos.py:22-24`

**Issue:** The class docstring states "Mirrors the ScreenshotManager interface shape: `__init__(base_dir)`, `start(name, headless) -> Optional[str]`, `stop() -> None`, `delete(path) -> None`." `ScreenshotManager` has none of these methods (its only public method is `capture(driver, name, subdirectory)`). The two classes serve different lifecycle roles and sharing an interface is not the design goal. The docstring creates a false expectation of substitutability.

**Fix:** Replace with an accurate description:
```python
class VideoManager:
    """Manages ffmpeg screen recording for smoke tests.

    Lifecycle: call start() before the test body, stop() in teardown.
    Call delete() to discard a retained recording on test pass.
    Returns None from start() whenever recording is unavailable.
    """
```

---

### IN-04: `configs/env.*.yaml` files have no `videos_dir` key — silent hardcoding

**File:** `configs/env.dev.yaml:1-15`, `configs/env.qa.yaml:1-15`, `configs/env.prod.yaml:1-15`

**Issue:** The env YAML files define `screenshots_dir` but have no `videos_dir` key, and `AppConfig` has no `videos_dir` attribute (see WR-04). The omission is silent — there is no warning or log when the hardcoded default is used. Since `screenshots_dir` is present in all three files, the absence of `videos_dir` is likely an oversight rather than intentional.

**Fix:** Add `videos_dir` to each env YAML after resolving WR-04:
```yaml
videos_dir: reports/videos
```

---

_Reviewed: 2026-05-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
