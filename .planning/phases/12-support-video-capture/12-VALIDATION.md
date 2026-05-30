---
phase: 12
slug: support-video-capture
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-30
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | `pytest.ini` (verify at Wave 0) |
| **Quick run command** | `pytest tests/unit/test_video_manager.py -v` |
| **Full suite command** | `pytest tests/unit/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/test_video_manager.py -v`
- **After every plan wave:** Run `pytest tests/unit/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | VID-02, VID-06 | — | N/A | unit | `pytest tests/unit/test_app_config.py -v` | ✅ (extend) | ⬜ pending |
| 12-01-02 | 01 | 1 | VID-01, VID-03, VID-04, VID-05 | T-12-02, T-12-03 | `subprocess.Popen` uses list (not shell=True); `stdin.write(b"q")` not SIGTERM | unit (mock) | `pytest tests/unit/test_video_manager.py -v` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | VID-02 | — | N/A | grep/import | `grep "record_video" configs/env.dev.yaml configs/env.qa.yaml configs/env.prod.yaml` | ✅ (modify) | ⬜ pending |
| 12-02-01 | 02 | 2 | VID-07 | — | hook uses `wrapper=True` (not deprecated hookwrapper) | unit (pytester/mock) | `pytest tests/unit/test_video_fixture.py -v` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 2 | VID-07 | — | fixture is opt-in (not autouse); smoke-test only by convention | unit (mock) | `pytest tests/unit/test_video_fixture.py -v` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 3 | VID-01, VID-03, VID-04, VID-05, VID-07 | T-12-02, T-12-03 | subprocess.Popen list args; graceful stop via stdin q | unit | `pytest tests/unit/test_video_manager.py tests/unit/test_video_fixture.py -v` | ❌ W0 | ⬜ pending |
| 12-03-02 | 03 | 3 | VID-06 | — | N/A | grep | `grep "reports/videos/" .gitignore` | ✅ (modify) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_video_manager.py` — new file; covers VID-01, VID-03, VID-04, VID-05 (VideoManager interface, headless guard, ffmpeg-absent guard, delete method)
- [ ] `tests/unit/test_video_fixture.py` — new file; covers VID-07 (hook + stash integration using monkeypatch/mock ffmpeg; no real browser)
- [ ] Extend `tests/unit/test_app_config.py` — add VID-02 test: `record_video` defaults to `False`, reads from YAML and env var `RECORD_VIDEO`

*All Wave 0 tests use `monkeypatch` and `tmp_path` — no real browser, no real ffmpeg required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ffmpeg actually records a visible video on macOS | VID-01 | Requires ffmpeg installed + Screen Recording permission | `brew install ffmpeg`, grant Screen Recording to Terminal, run a smoke test with `record_video: true` in env.dev.yaml, confirm `.mp4` file in `reports/videos/` after a failing test |
| Video is blank (black) without Screen Recording permission | — | macOS system permission, not testable in code | Run with `record_video: true` without granting permission; confirm non-empty but black `.mp4` produced |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING (❌) references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
