# Phase 12: Support Video Capture for Failed Tests - Research

**Researched:** 2026-05-30
**Domain:** ffmpeg subprocess screen capture + pytest hook integration
**Confidence:** HIGH (core patterns verified against official sources + installed runtime)

---

## Summary

Phase 12 adds failure-only video recording to smoke tests. Every smoke test starts an ffmpeg child process that records the display; on pass the file is deleted, on fail it is retained as a failure artifact alongside existing screenshots. The implementation requires three interlocking components: (1) a `VideoManager` class in `src/utils/videos.py` that mirrors `ScreenshotManager`; (2) a `video_recorder` pytest fixture that owns subprocess lifecycle; and (3) a `pytest_runtest_makereport` hook that stores pass/fail outcome into `item.stash` so the fixture teardown can read it.

All three design decisions carry LOW implementation risk: the pytest stash pattern is documented in official pytest docs; ffmpeg subprocess management is a well-understood POSIX pattern; and the `ScreenshotManager` precedent in `src/utils/screenshots.py` provides a concrete interface to mirror.

The one legitimate complexity is cross-platform ffmpeg input device naming: macOS uses `-f avfoundation -i "<index>"` while Linux uses `-f x11grab -i :0.0`. The platform-selection logic must be isolated in one place (`VideoManager._build_cmd()`).

**Primary recommendation:** Use `wrapper=True, tryfirst=True` on the `pytest_runtest_makereport` hook (new-style, supported in pluggy 1.x / pytest 8.x). Start ffmpeg with `stdin=subprocess.PIPE`, `stdout=subprocess.DEVNULL`, `stderr=subprocess.DEVNULL`. Stop by writing `b"q"` to stdin then calling `process.wait(timeout=10)` with a `kill()` fallback. Delete the file if `report.get("call")` is not failed and not skipped.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use ffmpeg via subprocess — no Python package for recording; spawn ffmpeg as a child process to capture the screen. Requires `ffmpeg` installed on host (`brew install ffmpeg` / `apt install ffmpeg`).
- **D-02:** When `--headless` is active, skip recording silently and log a WARNING. No Xvfb dependency added. CI headless runs produce no video.
- **D-03:** Recording controlled by `record_video: true/false` in `configs/env.*.yaml`. Off by default (`false`).
- **D-04:** Recording applies to smoke tests only (`tests/smoke/`). Unit tests have no browser, no recording attempted.
- **D-05:** Failures only — record every smoke test, but delete the video file if the test passes. Only failed tests retain their video.
- **D-06:** Video files saved to `reports/videos/<timestamp>_<test_name>.mp4` (H.264/MP4). Naming mirrors `ScreenshotManager`: `YYYYMMDD_HHMMSS_<safe_name>.mp4`. Directory: `reports/videos/`.

### Claude's Discretion
- **Integration point:** `VideoManager` in `src/utils/videos.py` mirroring `ScreenshotManager`. Wire via `video_recorder` fixture in `tests/conftest.py`. Use `pytest_runtest_makereport` hook for pass/fail detection. `AppConfig` gets `record_video: bool`. `VIDEO_DIR` added to `src/core/constants.py`.

### Deferred Ideas (OUT OF SCOPE)
- CI/Xvfb setup guide
- Video retention policy / auto-cleanup (keep last N)
- HTML report embedding
</user_constraints>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| YAML config flag (`record_video`) | Config layer (`AppConfig`) | — | Follows existing pattern for `headless`, `browser` flags |
| Video directory + naming constants | Constants (`src/core/constants.py`) | — | Mirrors `SCREENSHOT_DIR`, `SCREENSHOT_DATE_FORMAT` |
| ffmpeg subprocess lifecycle | Utility class (`src/utils/videos.py`) | — | Encapsulates OS-specific command + process start/stop |
| Fixture wiring + stash access | Test infrastructure (`tests/conftest.py`) | — | Fixture owns driver lifecycle; hook stores outcome |
| Pass/fail detection | Hook (`pytest_runtest_makereport`) | Fixture teardown | Hook populates stash; fixture reads it |
| File retention decision | Fixture teardown | `VideoManager` | Fixture decides keep/delete based on stash; `VideoManager` exposes `delete()` |
| .gitignore exclusion | Repository config (`.gitignore`) | — | `reports/videos/` must be added like `reports/screenshots/` |

---

## Technical Findings

### ffmpeg Command Reference (macOS / Linux)

#### Device Discovery

**macOS** — list AVFoundation devices to find screen index:
```bash
ffmpeg -hide_banner -f avfoundation -list_devices true -i ""
```
Output includes lines like `[1] Capture screen 0`. The bracketed number `[1]` is the index to use in `-i "1"`. Primary display is typically index `1` (index `0` is often FaceTime camera). [VERIFIED: ffmpeg-cookbook.com/en/articles/screen-recording/]

**Linux** — DISPLAY env var gives the X display:
```bash
echo $DISPLAY   # typically :0 or :0.0
```
[VERIFIED: ffmpeg-cookbook.com/en/articles/screen-recording/]

#### Recording Commands

**macOS (AVFoundation):**
```bash
ffmpeg -y \
  -f avfoundation \
  -framerate 15 \
  -i "1" \
  -c:v libx264 \
  -preset ultrafast \
  -crf 28 \
  -pix_fmt yuv420p \
  output.mp4
```
Notes:
- `-y` overwrites output without prompt [VERIFIED: ffmpeg docs]
- `"1"` is the screen capture device index (parsed at runtime) [VERIFIED: ffmpeg-cookbook.com]
- `-framerate 15` is sufficient for test debugging; reduces file size vs 30fps [ASSUMED — 15fps is a reasonable test trade-off]
- `-preset ultrafast` is mandatory for real-time capture to prevent dropped frames [VERIFIED: ffmpeg-cookbook.com]
- `-crf 28` trades quality for smaller files (range 0–51; 23 is default, 28 is acceptable for test artifacts) [ASSUMED — value not standardized]
- `-pix_fmt yuv420p` required for broad player compatibility [VERIFIED: ffmpeg-cookbook.com]

**Linux (x11grab):**
```bash
ffmpeg -y \
  -f x11grab \
  -framerate 15 \
  -video_size 1920x1080 \
  -i :0.0 \
  -c:v libx264 \
  -preset ultrafast \
  -crf 28 \
  -pix_fmt yuv420p \
  output.mp4
```
Notes:
- `-video_size` must match the actual display resolution [VERIFIED: ffmpeg-cookbook.com]
- `-i :0.0` uses `$DISPLAY` env var value; fall back to `:0.0` if DISPLAY is unset [ASSUMED — standard Linux convention]
- Wayland: `x11grab` does NOT work under Wayland; requires `wf-recorder` or XWayland [CITED: ffmpeg-cookbook.com/en/articles/screen-recording/]

**Windows (gdigrab) — not in scope but documented for completeness:**
```bash
ffmpeg -y -f gdigrab -framerate 15 -i desktop -c:v libx264 -preset ultrafast -crf 28 -pix_fmt yuv420p output.mp4
```
[CITED: coreygoldberg.com/posts/python-selenium-video-recording/ — reference only]

#### macOS Screen Index Discovery (Python)

The screen index cannot be hardcoded. Parse it at runtime:
```python
import subprocess, re

def _find_macos_screen_index() -> str:
    """Return the AVFoundation screen device index, default '1' on failure."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True, text=True, timeout=5
        )
        # Output appears on stderr for list_devices
        combined = result.stdout + result.stderr
        match = re.search(r"\[(\d+)\]\s+Capture screen", combined)
        if match:
            return match.group(1)
    except Exception:
        pass
    return "1"   # safe default for most macOS systems
```
[ASSUMED — regex pattern based on observed ffmpeg output format; verified format from multiple sources]

---

### Python subprocess Management

#### Starting ffmpeg

```python
import subprocess, sys

proc = subprocess.Popen(
    cmd,                          # list of strings — never a shell string
    stdin=subprocess.PIPE,        # required for 'q' quit signal
    stdout=subprocess.DEVNULL,    # suppress ffmpeg progress output
    stderr=subprocess.DEVNULL,    # suppress ffmpeg banner + stats
)
```

Key points:
- `stdin=subprocess.PIPE` is required; sending `b"q"` to a non-pipe stdin raises `BrokenPipeError` [VERIFIED: github.com/kkroening/ffmpeg-python/issues/162]
- `stdout=subprocess.DEVNULL` + `stderr=subprocess.DEVNULL` prevent pipe buffer fill deadlock — ffmpeg writes verbose output and a full pipe blocks the subprocess [VERIFIED: imageio-ffmpeg issue #17 + ffmpeg-python issue #195]
- Use a list for `cmd`, not a shell string — avoids `shell=True` security risk and `shlex` parsing overhead [ASSUMED — standard Python subprocess best practice]

#### Stopping ffmpeg Gracefully

```python
def _stop_process(proc: subprocess.Popen, timeout: int = 10) -> None:
    """Send 'q' to ffmpeg stdin, wait for clean exit, fallback to kill."""
    if proc.poll() is not None:
        return  # already terminated
    try:
        proc.stdin.write(b"q")
        proc.stdin.flush()
        proc.stdin.close()
        proc.wait(timeout=timeout)
    except (BrokenPipeError, OSError):
        # Process died before we could write
        pass
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
```

Why `b"q"` not `proc.terminate()` / `SIGTERM`:
- `SIGTERM` and `SIGKILL` interrupt ffmpeg mid-write, resulting in a truncated/unplayable MP4 (moov atom not written) [VERIFIED: github.com/Ch00k/ffmpy/issues/11]
- Sending `b"q"` triggers ffmpeg's built-in graceful shutdown which flushes and finalizes the file [VERIFIED: ffmpeg-python/issues/162]
- `proc.wait(timeout=10)` prevents the fixture teardown from hanging indefinitely if ffmpeg stalls [VERIFIED: subprocess docs pattern]

#### Edge Cases

| Scenario | Behavior | Mitigation |
|----------|----------|------------|
| ffmpeg not on PATH | `FileNotFoundError` on `Popen` | Catch in `VideoManager.start()`, log WARNING, set `self._proc = None`, recording disabled for session |
| Process crashes before teardown | `proc.poll()` returns non-None | Guard with `if proc.poll() is not None: return` before writing to stdin |
| Test crashes before fixture yield | `yield` never reached | Python `try/finally` in fixture ensures teardown always runs |
| ffmpeg ignores `q` (hangs) | `wait(timeout=10)` raises `TimeoutExpired` | `proc.kill()` + `proc.wait()` forcefully terminates; file may be unplayable |
| Disk full | `ffmpeg` exits non-zero during recording | `proc.poll()` check at stop time detects early exit; log WARNING |
| Video file 0 bytes (ffmpeg failed to start recording) | File exists but is empty/invalid | Check `os.path.getsize(path) > 0` before logging "video saved"; otherwise log WARNING |

[ASSUMED — edge case analysis based on subprocess and ffmpeg behavior patterns; individual items not individually verified against official docs]

---

### pytest runtest_makereport Hook Pattern

#### Verified Pattern (pytest 8.4.2, pluggy 1.x)

Both `wrapper=True` (new-style) and `hookwrapper=True` (old-style) are supported. Use `wrapper=True` as it is the current documented form. [VERIFIED: `pytest.hookimpl.__call__` signature in installed pytest 8.4.2]

```python
# tests/conftest.py  (add at module level)
from pytest import StashKey, CollectReport

_phase_report_key: StashKey[dict[str, CollectReport]] = StashKey()


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    rep = yield   # new-style: yield returns the report directly
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep
    return rep
```

[VERIFIED: docs.pytest.org/en/stable/example/simple.html — exact code pattern from official docs]

#### Fixture Reading the Stash

```python
@pytest.fixture(scope="function")
def video_recorder(request, app_config, driver):
    """Start video recording; retain file only if test fails."""
    manager = VideoManager(app_config)
    video_path = manager.start(request.node.name)   # returns path or None
    yield video_path

    # --- teardown: read outcome ---
    report = request.node.stash.get(_phase_report_key, {})
    setup_ok = not report.get("setup", _PASS).failed
    call_failed = report.get("call", _PASS).failed or report.get("call", _PASS).skipped

    # Delete video if test passed (no failure in setup OR call)
    if setup_ok and not call_failed and video_path:
        manager.delete(video_path)
    elif video_path:
        logger.info("Video retained (test failed): %s", video_path)

    manager.stop()
```

Where `_PASS` is a sentinel with `.failed = False, .skipped = False`.

**Important timing constraint:** The `_phase_report_key` stash is populated by the `pytest_runtest_makereport` hook for the `"call"` phase AFTER the test body returns but BEFORE the fixture teardown (code after `yield`) executes. This is the fundamental guarantee that makes the pattern work. [VERIFIED: docs.pytest.org/en/stable/example/simple.html]

---

### VideoManager Class Design

#### Interface (mirrors ScreenshotManager exactly)

```python
# src/utils/videos.py
from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.constants import VIDEO_DATE_FORMAT, VIDEO_DIR
from src.core.logger import get_logger
from src.utils.files import ensure_dir, safe_filename

logger = get_logger("videos")


class VideoManager:
    """Manages ffmpeg screen recording for smoke tests."""

    def __init__(self, base_dir: str = VIDEO_DIR) -> None:
        self._base_dir = Path(base_dir)
        self._proc: Optional[subprocess.Popen] = None
        self._current_path: Optional[str] = None

    def start(self, name: str) -> Optional[str]:
        """Start recording; return output path, or None if recording unavailable."""
        ...

    def stop(self) -> None:
        """Stop recording subprocess gracefully."""
        ...

    def delete(self, path: str) -> None:
        """Delete a video file (call on test pass)."""
        ...
```

#### Constants to Add (src/core/constants.py)

```python
# Video
VIDEO_DIR: str = "reports/videos"
VIDEO_DATE_FORMAT: str = "%Y%m%d_%H%M%S"   # same as SCREENSHOT_DATE_FORMAT — can reuse
```

Since `VIDEO_DATE_FORMAT` would be identical to `SCREENSHOT_DATE_FORMAT`, the planner can choose to either define a separate constant (preferred for naming clarity) or reuse the existing one. [ASSUMED — design choice]

#### AppConfig Field (src/core/config.py)

Follow the existing `_resolve_bool` pattern:
```python
self.record_video: bool = self._resolve_bool("RECORD_VIDEO", "record_video", False)
```

Env var override: `RECORD_VIDEO=true pytest` enables recording without YAML change. [VERIFIED: existing `_resolve_bool` pattern in `src/core/config.py`]

---

### Edge Cases and Risks

#### 1. Headless Guard

`app_config.headless` is set in `app_config` fixture (session-scoped). Check it in `VideoManager.start()` or at the fixture level before starting the process:

```python
if app_config.headless:
    logger.warning("Video recording skipped: headless mode active")
    return None
```

[VERIFIED: CONTEXT.md D-02; `app_config.headless` field verified in `src/core/config.py`]

#### 2. ffmpeg Availability Check

Use `shutil.which("ffmpeg")` before attempting `Popen`:
```python
import shutil
if shutil.which("ffmpeg") is None:
    logger.warning("ffmpeg not found on PATH — video recording disabled")
    return None
```

`shutil.which` is stdlib, no import overhead. [ASSUMED — standard pattern; shutil.which is Python stdlib since 3.3]

#### 3. Platform Detection

```python
import platform
system = platform.system()  # "Darwin", "Linux", "Windows"
```

Gate the x11grab path on `$DISPLAY` being set; if `DISPLAY` is not set on Linux, ffmpeg will fail:
```python
if system == "Linux" and not os.environ.get("DISPLAY"):
    logger.warning("No DISPLAY env var — video recording disabled (Wayland?)")
    return None
```
[ASSUMED — reasonable guard based on x11grab requirements]

#### 4. pytest-xdist Compatibility

`pytest-xdist` is NOT installed in this project. [VERIFIED: `pip show pytest-xdist` returned "not found"]. No parallel recording conflict risk for this phase. If xdist is added later, the `request.node.name` will be unique per test, so filenames won't collide — but the `_phase_report_key` StashKey approach works fine with xdist because each worker has its own item stash. [ASSUMED — StashKey is per-item, not global]

#### 5. Video File Cleanup on Process Crash

If the test runner itself crashes (SIGKILL, OOM), fixture teardown does not run and the orphaned ffmpeg subprocess will continue recording until it is killed or the system is rebooted. This is acceptable for a developer tool; document as known limitation. [ASSUMED — analysis of Python fixture guarantee scope]

#### 6. .gitignore

`reports/videos/` must be added to `.gitignore` (same pattern as `reports/screenshots/`). Currently missing. [VERIFIED: read `.gitignore` — `reports/screenshots/` is listed but `reports/videos/` is not]

#### 7. File Size

At `-crf 28 -preset ultrafast -framerate 15`, a 1-minute recording at 1920x1080 produces approximately 20-60 MB. [ASSUMED — estimate from general H.264 compression knowledge; not benchmarked]

---

## Validation Architecture

`nyquist_validation` is enabled (verified in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pytest.ini` or `pyproject.toml` (check at Wave 0) |
| Quick run | `pytest tests/unit/test_video_manager.py -v` |
| Full suite | `pytest tests/unit/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| VID-01 | `VideoManager` mirrors `ScreenshotManager` interface (`__init__`, `start`, `stop`, `delete`) | unit | `pytest tests/unit/test_video_manager.py -v` | No — Wave 0 |
| VID-02 | `AppConfig.record_video` defaults to `False`, reads from YAML and env var | unit | `pytest tests/unit/test_app_config.py -v` | Partial — extend |
| VID-03 | `VideoManager.start()` returns `None` when `headless=True` | unit (mock) | `pytest tests/unit/test_video_manager.py::TestVideoManagerHeadless -v` | No — Wave 0 |
| VID-04 | `VideoManager.start()` returns `None` when ffmpeg not on PATH | unit (mock shutil.which) | `pytest tests/unit/test_video_manager.py::TestVideoManagerNoFfmpeg -v` | No — Wave 0 |
| VID-05 | `VideoManager.delete()` removes file from filesystem | unit | `pytest tests/unit/test_video_manager.py::TestVideoManagerDelete -v` | No — Wave 0 |
| VID-06 | `VIDEO_DIR` and `VIDEO_DATE_FORMAT` constants exist in `src/core/constants.py` | unit | `pytest tests/unit/test_constants.py -v` (or inline import check) | No — Wave 0 |
| VID-07 | Hook + fixture: video deleted on test pass, retained on fail | integration (mock ffmpeg) | `pytest tests/unit/test_video_fixture.py -v` | No — Wave 0 |

All tests are unit-level (no real browser, no real ffmpeg required) using `monkeypatch`/`tmp_path`. Only VID-07 requires a mini pytest fixture integration test using `pytester` or `monkeypatch`.

### Sampling Rate

- Per task commit: `pytest tests/unit/test_video_manager.py -v`
- Per wave merge: `pytest tests/unit/ -v`
- Phase gate: full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_video_manager.py` — covers VID-01, VID-03, VID-04, VID-05
- [ ] `tests/unit/test_video_fixture.py` — covers VID-07 (hook + stash integration)
- [ ] Extend `tests/unit/test_app_config.py` — cover VID-02 (`record_video` field)

---

## Implementation Guidance

### File Change Inventory

| File | Change | Note |
|------|--------|------|
| `src/core/constants.py` | Add `VIDEO_DIR`, `VIDEO_DATE_FORMAT` | Mirror `SCREENSHOT_DIR` |
| `src/core/config.py` | Add `self.record_video: bool` field | Use `_resolve_bool` |
| `src/utils/videos.py` | New file — `VideoManager` class | Mirror `ScreenshotManager` |
| `tests/conftest.py` | Add `_phase_report_key` stash key, `pytest_runtest_makereport` hook, `video_recorder` fixture | Three additions |
| `configs/env.dev.yaml` | Add `record_video: false` | Off by default |
| `configs/env.qa.yaml` | Add `record_video: false` | Off by default |
| `configs/env.prod.yaml` | Add `record_video: false` | Off by default |
| `.gitignore` | Add `reports/videos/` | Mirror `reports/screenshots/` |
| `tests/unit/test_video_manager.py` | New file — unit tests | Wave 0 gap |

### Decision Summary for Planner

1. **ffmpeg stop method:** Write `b"q"` to stdin, then `process.wait(timeout=10)`, then `process.kill()` fallback. Do NOT use `SIGTERM`. [VERIFIED]

2. **Hook style:** Use `@pytest.hookimpl(wrapper=True, tryfirst=True)` with `rep = yield` (new-style). Both styles work in pytest 8.4.2 but `wrapper=True` is current. [VERIFIED]

3. **Stash key type:** `StashKey[dict[str, CollectReport]]()` at module level in `conftest.py`. [VERIFIED: official pytest docs]

4. **Pass/fail decision logic in fixture teardown:**
   - Get `report = request.node.stash.get(_phase_report_key, {})`
   - Fail condition: `report.get("setup", ...).failed` OR `report.get("call", ...).failed`
   - If NO failure: call `manager.delete(video_path)`
   - If failure: log path, retain file

5. **Platform branching in `VideoManager._build_cmd()`:**
   - `platform.system() == "Darwin"` → avfoundation + screen index (parsed via `list_devices`)
   - `platform.system() == "Linux"` + `$DISPLAY` set → x11grab + `:0.0` (or `$DISPLAY` value)
   - Otherwise (Windows / Wayland / no DISPLAY) → log WARNING, return `None`

6. **`video_recorder` fixture scope:** `function` (same as `driver`). The fixture depends on `driver` so it must be function-scoped.

7. **`video_recorder` fixture location:** `tests/conftest.py` (shared conftest), not a smoke-only conftest. The fixture activates only when `app_config.record_video` is `True`, so unit tests that don't request it are unaffected.

8. **Output path construction:** Use same `safe_filename(request.node.name)` from `src/utils/files.py` — already handles pytest node names like `test_foo[param]`.

9. **`reports/videos/` directory:** Call `ensure_dir()` from `src/utils/files.py` before starting ffmpeg, same as `ScreenshotManager`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `-framerate 15 -crf 28` are reasonable defaults for test artifact quality/size | ffmpeg Command Reference | File too large (use 10fps) or too small/blurry (use crf 23). Adjust in constants. |
| A2 | macOS primary display is always at AVFoundation index `1` (index `0` is camera) | ffmpeg Command Reference | Recording captures wrong device. Mitigated by runtime `list_devices` parse. |
| A3 | `$DISPLAY` env var equals `:0.0` on most Linux X11 setups | ffmpeg Command Reference | Recording fails on multi-display or non-standard display. Use `os.environ.get("DISPLAY", ":0.0")`. |
| A4 | `StashKey` works correctly when accessed inside fixture teardown (after `yield`) | pytest Hook Pattern | Stash might be empty; guard with `.get()` and a safe default. |
| A5 | ffmpeg outputs `list_devices` info to stderr (not stdout) | macOS screen index discovery | Regex misses the device list. Use `combined = stdout + stderr` to be safe. |
| A6 | `VIDEO_DATE_FORMAT` can be identical to `SCREENSHOT_DATE_FORMAT` | Constants | No conflict — either reuse the existing constant or define a separate one. |
| A7 | `record_video` fixture should be opt-in (requested by test, not auto-used) | Fixture design | If `autouse=True` and `app_config.record_video=False`, overhead is minimal but non-zero. Opt-in is cleaner. |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9.13 | All code | Yes | 3.9.13 | — |
| pytest | Test runner | Yes | 8.4.2 | — |
| ffmpeg | Video capture | No | — (not installed) | Log WARNING, disable recording silently |
| pytest-xdist | Parallel runs | No | — (not installed) | N/A — not needed for this phase |
| macOS AVFoundation | macOS screen capture | Yes (macOS 26.5) | OS-native | N/A — Linux path is separate |

**Missing dependencies with no fallback:**
- None that block execution. `ffmpeg` absence is handled gracefully by `VideoManager.start()` returning `None`.

**Missing dependencies with fallback:**
- `ffmpeg`: not installed on development machine. Install: `brew install ffmpeg`. VideoManager silently disables if absent.

**macOS Screen Recording Permission:** macOS requires explicit "Screen Recording" permission granted to the terminal application under System Settings > Privacy & Security > Screen Recording. Without this, ffmpeg will produce a black/empty video. This is a one-time setup step, not a code issue. [CITED: ffmpeg-cookbook.com/en/articles/screen-recording/]

---

## Open Questions

1. **Video file size management**
   - What we know: H.264 at `-crf 28 -framerate 15` produces reasonable sizes
   - What's unclear: No project retention policy defined (deferred per CONTEXT.md)
   - Recommendation: Proceed with current settings; add a note in `.gitignore` comment

2. **Wayland support**
   - What we know: `x11grab` does not work on Wayland; `wf-recorder` is an alternative
   - What's unclear: Developer machines may use Wayland (Ubuntu 22+, Fedora 38+)
   - Recommendation: Detect `$WAYLAND_DISPLAY` env var; if set, log WARNING and skip recording (same as headless). Do not add `wf-recorder` dependency.

3. **macOS Screen Recording permission**
   - What we know: Requires one-time system permission grant
   - What's unclear: Will fail silently (black video) if not granted, not with an error
   - Recommendation: Document in README/CLAUDE.md; add a log message "If video is blank, grant Screen Recording permission"

---

## Sources

### Primary (HIGH confidence)
- [pytest official docs — Making test result information available in fixtures](https://docs.pytest.org/en/stable/example/simple.html) — `phase_report_key`, `pytest_runtest_makereport`, `StashKey`, fixture stash access pattern
- [pluggy `HookimplMarker.__call__` signature](https://pypi.org/project/pluggy/) — verified `wrapper=True` and `hookwrapper=True` both supported in pluggy 1.x (installed pytest 8.4.2)
- [ffmpeg-cookbook.com — Screen Recording](https://ffmpeg-cookbook.com/en/articles/screen-recording/) — macOS avfoundation command, Linux x11grab command, `-preset ultrafast` rationale, `-pix_fmt yuv420p` compatibility requirement
- `src/utils/screenshots.py` — ScreenshotManager interface to mirror (read directly from codebase)
- `tests/conftest.py` — existing fixture patterns (read directly from codebase)
- `src/core/config.py` — `_resolve_bool` pattern for `record_video` field (read directly)

### Secondary (MEDIUM confidence)
- [coreygoldberg.com — Python Selenium Video Recording](https://coreygoldberg.com/posts/python-selenium-video-recording/) — confirms `proc.terminate()` + `proc.wait()` pattern for POSIX; `CTRL_BREAK_EVENT` for Windows
- [ffmpeg-python issue #162](https://github.com/kkroening/ffmpeg-python/issues/162) — `process.stdin.write(b"q")` + `communicate(timeout=)` for clean stop
- [imageio-ffmpeg issue #17](https://github.com/imageio/imageio-ffmpeg/issues/17) — confirms `stdout=DEVNULL, stderr=DEVNULL` needed to prevent pipe deadlock

### Tertiary (LOW confidence)
- WebSearch results on x11grab / Wayland detection — general ecosystem consensus, not verified against single authoritative source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no third-party libraries beyond stdlib subprocess; ffmpeg is a known tool
- Architecture: HIGH — mirrors existing ScreenshotManager pattern exactly; verified from codebase
- pytest hook pattern: HIGH — verified against official docs and installed pytest 8.4.2
- ffmpeg subprocess stop method: HIGH — verified across multiple authoritative sources (ffmpeg-python issues)
- Platform command specifics: MEDIUM — macOS avfoundation verified; Linux x11grab well-documented but Wayland caveat is real
- Edge cases: MEDIUM — subprocess crash scenarios are reasoned, not tested

**Research date:** 2026-05-30
**Valid until:** 2026-08-30 (stable tooling — pytest hooks and ffmpeg CLI are not fast-moving)

---

## RESEARCH COMPLETE
