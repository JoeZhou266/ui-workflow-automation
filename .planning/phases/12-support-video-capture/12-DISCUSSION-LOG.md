# Phase 12: Support Video Capture for Failed Tests - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 12-support-video-capture
**Areas discussed:** Recording library, Activation & scope, Save policy

---

## Recording library

| Option | Description | Selected |
|--------|-------------|----------|
| ffmpeg subprocess | Call ffmpeg via subprocess; requires ffmpeg binary; zero Python bloat; cross-platform; standard in CI | ✓ |
| pytest-video plugin | Wraps ffmpeg, pytest-native lifecycle hooks; still requires ffmpeg binary | |
| opencv-python screenshots | Stitch Selenium screenshots into video; no external binary but high CPU, low FPS, large files | |

**User's choice:** ffmpeg subprocess

---

## Recording library — headless mode

| Option | Description | Selected |
|--------|-------------|----------|
| Skip recording silently in headless mode | Auto-disable when --headless; log WARNING; no Xvfb dependency | ✓ |
| Require virtual display (Xvfb) for headless recording | Add xvfbwrapper; enables CI video; more setup required | |
| You decide | Let Claude decide | |

**User's choice:** Skip recording silently in headless mode

---

## Activation

| Option | Description | Selected |
|--------|-------------|----------|
| --record CLI flag | Opt-in via pytest CLI flag; no change to existing behavior | |
| Always-on when ffmpeg installed | Auto-detect ffmpeg at session start; no flag needed | |
| Config flag in env.*.yaml | record_video: true/false per environment; consistent with existing AppConfig pattern | ✓ |

**User's choice:** Config flag in env.*.yaml

---

## Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Smoke tests only | Only tests/smoke/ have a real browser; unit tests have no WebDriver | ✓ |
| Any test using driver fixture | Same practical effect since driver fixture is browser-only | |

**User's choice:** Smoke tests only

---

## Save policy — retention

| Option | Description | Selected |
|--------|-------------|----------|
| Failures only — delete on pass | Record all, delete on pass; mirrors screenshot pattern; minimal disk usage | ✓ |
| Keep all videos | Never delete; simple code; storage grows unboundedly | |
| Keep failures + last N passing videos | Retention logic complexity; unclear benefit | |

**User's choice:** Failures only — delete on pass

---

## Save policy — location/format

| Option | Description | Selected |
|--------|-------------|----------|
| reports/videos/\<timestamp\>_\<test_name\>.mp4 | Mirrors reports/screenshots/; MP4 H.264; universally playable | ✓ |
| reports/videos/\<test_name\>/\<timestamp\>.mp4 | Group by test name; many subdirectories | |

**User's choice:** reports/videos/\<timestamp\>_\<test_name\>.mp4

---

## Claude's Discretion

- **Integration point** (not selected for discussion): `VideoManager` class in `src/utils/videos.py` mirroring `ScreenshotManager`; wired via `video_recorder` fixture in `tests/conftest.py` with `pytest_runtest_makereport` hook.

## Deferred Ideas

- CI/Xvfb setup documentation
- Video retention / auto-cleanup policy
- HTML report embedding
