---
phase: 12-support-video-capture
verified: 2026-05-30T18:48:00Z
status: human_needed
score: 13/13 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Enable record_video: true in configs/env.dev.yaml, install ffmpeg (brew install ffmpeg), grant Screen Recording permission to Terminal, run a smoke test that deliberately fails (e.g. assert False in test body), check reports/videos/ for a retained .mp4 file"
    expected: "A non-empty .mp4 file exists in reports/videos/ after the failing test; no file exists after a passing test"
    why_human: "Cannot exercise real ffmpeg subprocess + real pytest pass/fail lifecycle in a unit-test context; requires actual ffmpeg on PATH, display access, and a real browser session to exercise the full end-to-end path"
---

# Phase 12: Support Video Capture Verification Report

**Phase Goal:** Add video capture support — when record_video is enabled and ffmpeg is available, the pytest smoke-test fixture records the browser session; recordings are retained on test failure and deleted on pass.
**Verified:** 2026-05-30T18:48:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | VIDEO_DIR and VIDEO_DATE_FORMAT constants exist in src/core/constants.py | VERIFIED | Lines 19-20 of constants.py: `VIDEO_DIR: str = "reports/videos"`, `VIDEO_DATE_FORMAT: str = "%Y%m%d_%H%M%S"` |
| 2  | AppConfig.record_video defaults to False and reads from YAML + env var | VERIFIED | Line 54 config.py: `self.record_video: bool = self._resolve_bool("RECORD_VIDEO", "record_video", False)`; 6 passing tests in test_video_constants_and_config.py confirm YAML override and env var override |
| 3  | VideoManager.start() returns None when headless=True (no ffmpeg spawn) | VERIFIED | Lines 40-43 videos.py; TestVideoManagerHeadless 2/2 tests pass; `_proc` stays None |
| 4  | VideoManager.start() returns None when ffmpeg not on PATH | VERIFIED | Lines 44-47 videos.py: `shutil.which("ffmpeg") is None` guard; TestVideoManagerNoFfmpeg 2/2 tests pass |
| 5  | VideoManager.start() returns a file path string when ffmpeg is available and not headless | VERIFIED | Lines 61-76 videos.py; TestVideoManagerStart passes on Darwin mock (3/3 tests) |
| 6  | VideoManager.stop() gracefully stops via stdin 'q' signal | VERIFIED | Line 86 videos.py: `self._proc.stdin.write(b"q")`; TestVideoManagerStop 6/6 tests pass including kill-on-timeout |
| 7  | VideoManager.delete() removes the file from the filesystem | VERIFIED | Lines 100-108 videos.py; TestVideoManagerDelete 3/3 tests pass including no-op on FileNotFoundError |
| 8  | All three env YAML configs have record_video: false | VERIFIED | dev.yaml line 4, qa.yaml, prod.yaml all contain `record_video: false` (confirmed by grep) |
| 9  | pytest_runtest_makereport hook stores pass/fail outcome in item.stash | VERIFIED | Lines 20-25 conftest.py: `@pytest.hookimpl(wrapper=True, tryfirst=True)`, `item.stash.setdefault(_phase_report_key, {})[rep.when] = rep`; TestStashKeyConstant + TestHookPresence all pass |
| 10 | video_recorder fixture starts recording at test start and stops at teardown | VERIFIED | Lines 91-127 conftest.py; TestVideoRecorderBehavior::test_stop_always_called PASS |
| 11 | Video file is deleted when the test passes | VERIFIED | Lines 121-125 conftest.py: `manager.delete(video_path)` in else branch; TestVideoRecorderBehavior::test_delete_called_on_pass PASS |
| 12 | Video file is retained when the test fails | VERIFIED | Lines 122-123 conftest.py: retain path logged; TestVideoRecorderBehavior::test_delete_not_called_on_fail PASS |
| 13 | video_recorder fixture is opt-in (not autouse); unit tests are unaffected | VERIFIED | No `autouse` keyword in conftest.py for video_recorder; 284 unit tests pass with 0 failures |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/core/constants.py` | VIDEO_DIR and VIDEO_DATE_FORMAT constants | VERIFIED | Lines 18-20: `# Video` block with both constants |
| `src/core/config.py` | record_video bool field on AppConfig | VERIFIED | Line 54: `_resolve_bool("RECORD_VIDEO", "record_video", False)`; VIDEO_DIR imported line 20 |
| `src/utils/videos.py` | VideoManager class with start/stop/delete interface | VERIFIED | 186-line file; all 4 methods (start, stop, delete, _build_cmd) present and substantive; 30 tests pass |
| `configs/env.dev.yaml` | record_video: false | VERIFIED | Line 4: `record_video: false` immediately after `headless: false` |
| `configs/env.qa.yaml` | record_video: false | VERIFIED | Confirmed by grep |
| `configs/env.prod.yaml` | record_video: false | VERIFIED | Confirmed by grep |
| `tests/conftest.py` | _phase_report_key StashKey, pytest_runtest_makereport hook, video_recorder fixture | VERIFIED | All three present; hook uses wrapper=True, tryfirst=True; fixture is function-scoped, opt-in |
| `tests/unit/test_video_manager.py` | Unit tests covering VID-01 through VID-07 | VERIFIED | 30 tests across 9 classes, all passing |
| `.gitignore` | reports/videos/ exclusion | VERIFIED | Line 17: `reports/videos/` immediately after `reports/screenshots/` on line 16; comment updated |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| src/core/config.py | src/core/constants.py | import VIDEO_DIR | WIRED | Line 20 of config.py: `VIDEO_DIR` in import block |
| src/utils/videos.py | src/core/constants.py | import VIDEO_DIR, VIDEO_DATE_FORMAT | WIRED | Lines 12-13 of videos.py; both used at lines 26, 53 |
| src/utils/videos.py | src/utils/files.py | ensure_dir, safe_filename | WIRED | Line 14 of videos.py; both used at lines 56, 54 |
| tests/conftest.py | src/utils/videos.py | import VideoManager inside fixture | WIRED | Line 100: `from src.utils.videos import VideoManager`; used at line 104 |
| pytest_runtest_makereport hook | video_recorder fixture teardown | item.stash / request.node.stash | WIRED | Hook at line 24 stores to stash; fixture reads at line 110 `request.node.stash.get(_phase_report_key, {})` |

### Data-Flow Trace (Level 4)

Not applicable — no components render dynamic data from a database or API. VideoManager writes to the filesystem; the fixture reads from pytest's stash mechanism. Both are verified through unit tests rather than data-flow tracing.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| VideoManager.start() returns None for headless | `python -c "from src.utils.videos import VideoManager; m = VideoManager(); assert m.start('t', headless=True) is None"` | Exit 0 | PASS |
| VIDEO_DIR constant value | `python -c "from src.core.constants import VIDEO_DIR; assert VIDEO_DIR == 'reports/videos'"` | Exit 0 | PASS |
| record_video defaults to False | `python -c "from src.core.config import AppConfig; c = AppConfig(env='dev'); assert c.record_video is False"` | Exit 0 | PASS |
| All 284 unit tests pass | `pytest tests/unit/ -q` | 284 passed | PASS |
| Real ffmpeg end-to-end recording | Requires ffmpeg + display + real browser | Not testable without environment setup | SKIP (human needed) |

### Requirements Coverage

No formal REQUIREMENTS.md file exists in the project. VID-01 through VID-07 are defined inline in PLAN frontmatter. All plan-declared requirement IDs are accounted for:

| Requirement | Source Plan(s) | Description (derived from plan coverage) | Status | Evidence |
|-------------|---------------|------------------------------------------|--------|---------|
| VID-01 | 12-01, 12-03 | VideoManager interface: start/stop/delete/_build_cmd methods | SATISFIED | All 4 methods exist; 30 unit tests pass |
| VID-02 | 12-01, 12-03 | AppConfig.record_video bool field, default False, reads YAML + RECORD_VIDEO env var | SATISFIED | Line 54 config.py; 6 passing config tests |
| VID-03 | 12-01, 12-03 | VideoManager.start() returns None when headless=True | SATISFIED | Lines 40-43 videos.py; 2 passing tests |
| VID-04 | 12-01, 12-03 | VideoManager.start() returns None when ffmpeg absent or Linux without DISPLAY | SATISFIED | Lines 44-47, 133-156 videos.py; 3 passing tests |
| VID-05 | 12-01, 12-03 | VideoManager.delete() removes file, no-op on FileNotFoundError | SATISFIED | Lines 100-108 videos.py; 3 passing tests |
| VID-06 | 12-01, 12-03 | VIDEO_DIR = "reports/videos", VIDEO_DATE_FORMAT = "%Y%m%d_%H%M%S" | SATISFIED | Lines 19-20 constants.py; 2 passing tests |
| VID-07 | 12-02, 12-03 | pytest fixture: delete on pass, retain on fail, stash hook wired | SATISFIED | conftest.py fixture + hook; 14 passing behavioral tests in test_conftest_video_recorder.py |

All 7 requirement IDs are covered. No orphaned requirements detected.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | — |

Scanned `src/utils/videos.py` and `tests/conftest.py` for TODO, FIXME, placeholder patterns, empty return values, hardcoded empty data, and stub implementations. None found. All methods have substantive implementations.

### Human Verification Required

#### 1. End-to-End Video Recording on Real Browser

**Test:** Set `record_video: true` in `configs/env.dev.yaml`. Install ffmpeg (`brew install ffmpeg`). Grant Screen Recording permission to Terminal (System Settings > Privacy & Security > Screen Recording). Run a smoke test that is written to fail. Check `reports/videos/` for a retained `.mp4` file. Then run a smoke test that passes and confirm the `.mp4` file is deleted.

**Expected:** A non-empty `.mp4` file is created in `reports/videos/` during the failing test and remains after it ends. For the passing test, no file remains (it was created and then deleted by teardown).

**Why human:** Cannot exercise the real ffmpeg subprocess, the actual display capture pipeline, macOS AVFoundation device enumeration, or the real pytest pass/fail lifecycle end-to-end without ffmpeg installed and Screen Recording permission granted. The fixture teardown logic and VideoManager methods are all unit-tested with mocks, but the integration path from browser session to retained .mp4 artifact requires a live environment.

### Gaps Summary

No gaps. All 13 observable truths are verified by codebase inspection and 284 passing unit tests. The single human verification item is an integration test requiring a real display + ffmpeg, not a code deficiency.

---

_Verified: 2026-05-30T18:48:00Z_
_Verifier: Claude (gsd-verifier)_
