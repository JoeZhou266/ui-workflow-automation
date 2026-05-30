# Phase 12: Support Video Capture for Failed Tests - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable per-test browser video recording during Selenium smoke tests. Recordings are captured for every smoke test; on pass the video is discarded, on failure the video is retained as a failure artifact alongside existing screenshots.

</domain>

<decisions>
## Implementation Decisions

### Recording Library
- **D-01:** Use **ffmpeg via subprocess** — no Python package for recording itself; spawn ffmpeg as a child process to capture the screen. Requires `ffmpeg` to be installed on the host (`brew install ffmpeg` / `apt install ffmpeg`).
- **D-02:** When `--headless` is active, **skip recording silently** and log a WARNING. No virtual display (Xvfb) dependency added. CI headless runs simply produce no video.

### Activation & Scope
- **D-03:** Recording is controlled by a **`record_video: true/false` flag in `configs/env.*.yaml`** (same mechanism as `headless`, `browser`, etc. in `AppConfig`). Off by default (`false`) so existing runs are unaffected.
- **D-04:** Recording applies to **smoke tests only** (tests in `tests/smoke/`). Unit tests in `tests/unit/` have no browser — no recording attempted there.

### Save Policy
- **D-05:** **Failures only** — record every smoke test, but delete the video file if the test passes. Only failed tests retain their video. This mirrors the existing `ScreenshotManager` behavior (screenshots only captured on failure).
- **D-06:** Video files saved to **`reports/videos/<timestamp>_<test_name>.mp4`** (H.264 / MP4 container). Naming mirrors `ScreenshotManager`: `YYYYMMDD_HHMMSS_<safe_name>.mp4`. Directory: `reports/videos/` (parallel to `reports/screenshots/`).

### Claude's Discretion
- **Integration point:** Implement a `VideoManager` class in `src/utils/videos.py` mirroring the `ScreenshotManager` pattern. Wire it into `tests/conftest.py` via a new `video_recorder` fixture (function-scoped, wraps the `driver` fixture). Use pytest's `pytest_runtest_makereport` hook to detect pass/fail and trigger save-or-delete. `AppConfig` gets a `record_video: bool` field and `VIDEO_DIR` is added to `src/core/constants.py`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing pattern to mirror
- `src/utils/screenshots.py` — `ScreenshotManager` class; `VideoManager` must follow the same interface shape (`__init__(base_dir)`, method returning Optional[str] path)
- `src/core/constants.py` — add `VIDEO_DIR: str = "reports/videos"` and `VIDEO_DATE_FORMAT` here
- `src/core/config.py` — `AppConfig.__init__` pattern for reading YAML config fields; add `record_video: bool`
- `tests/conftest.py` — existing `driver` fixture (function-scoped) and pytest option registration pattern; new `video_recorder` fixture goes here

### Config files to update
- `configs/env.dev.yaml` — add `record_video: false` (off by default)
- `configs/env.qa.yaml` — add `record_video: false` (off by default)
- `configs/env.prod.yaml` — add `record_video: false` (off by default)

### Architecture reference
- `CLAUDE.md` — constraint: never use `time.sleep()` for synchronization; reporter artifacts follow `reports/` convention

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/utils/screenshots.py` (`ScreenshotManager`): Direct pattern to mirror. Constructor takes `base_dir`, `capture()` returns `Optional[str]` path. `VideoManager` in `src/utils/videos.py` follows the same shape.
- `src/utils/files.py` (`ensure_dir`, `safe_filename`): Already used by `ScreenshotManager`; reuse for video path construction.
- `tests/conftest.py` (pytest fixture pattern + `--headless` option): `record_video` config read from `AppConfig`; skip recording when `app_config.headless` is `True`.
- `src/core/constants.py` (`SCREENSHOT_DIR`, `SCREENSHOT_DATE_FORMAT`): Add `VIDEO_DIR` and `VIDEO_DATE_FORMAT` constants here.

### Established Patterns
- Failure artifacts go in `reports/` subdirectories, named `<timestamp>_<safe_name>.<ext>`.
- `AppConfig` reads from YAML via `_resolve()` / `_resolve_bool()` with env var override — `record_video` follows the same pattern.
- `ensure_dir()` is used before any file write — same for video output directory.

### Integration Points
- `tests/conftest.py`: New `video_recorder` fixture; `pytest_runtest_makereport` hook to detect outcome.
- `src/core/constants.py`: `VIDEO_DIR = "reports/videos"` constant.
- `src/core/config.py` (`AppConfig`): `self.record_video: bool` field.
- `configs/env.*.yaml`: `record_video: false` entry.

</code_context>

<specifics>
## Specific Ideas

- ffmpeg command should record from the display at test start and produce MP4 (H.264). The process is started at fixture setup and terminated at fixture teardown. The resulting file is deleted if the test passed.
- If ffmpeg is not found on PATH, log a WARNING and disable recording for the session rather than raising an error.
- Video filename safe-name derived from the pytest test node id (`request.node.name`), same way `ScreenshotManager` uses `safe_filename()`.

</specifics>

<deferred>
## Deferred Ideas

- **Integration point** was not discussed interactively — left to Claude's discretion (documented in decisions above).
- **CI/Xvfb setup guide** — could document how to run recorded smoke tests in Linux CI using Xvfb; belongs in docs/README, not code.
- **Video retention policy / auto-cleanup** — keeping the last N failure videos; out of scope for this phase.
- **HTML report embedding** — embed videos in a test results HTML page; separate phase.

</deferred>

---

*Phase: 12-support-video-capture*
*Context gathered: 2026-05-30*
