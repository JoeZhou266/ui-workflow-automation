---
phase: 12-support-video-capture
plan: "02"
subsystem: pytest-integration
tags: [video, pytest, fixture, hook, stash, conftest]
dependency_graph:
  requires:
    - src/utils/videos.py (VideoManager — created in 12-01)
    - src/core/config.py (AppConfig.record_video — created in 12-01)
  provides:
    - tests/conftest.py (_phase_report_key StashKey constant)
    - tests/conftest.py (pytest_runtest_makereport hook)
    - tests/conftest.py (video_recorder fixture)
  affects:
    - Any smoke test that requests video_recorder fixture
tech_stack:
  added:
    - pytest StashKey for cross-hook-to-fixture outcome passing
    - pytest hookimpl wrapper=True (new-style, not deprecated hookwrapper=True)
  patterns:
    - Hook-to-fixture stash pattern: hook stores outcome before teardown runs
    - _Pass sentinel class for graceful missing-stash handling
    - Fixture calls __wrapped__ to enable unit testing of generator teardown logic
key_files:
  created:
    - tests/unit/test_conftest_hook.py
    - tests/unit/test_conftest_video_recorder.py
  modified:
    - tests/conftest.py
decisions:
  - "wrapper=True (not hookwrapper=True) used for pytest 8.4.2 new-style hook wrapper"
  - "headless=app_config.headless or not app_config.record_video consolidates guard to single boolean for VideoManager"
  - "manager.stop() placed outside if video_path: block to always clean up process state"
  - "_Pass sentinel class (not None) avoids AttributeError on .failed access when stash is absent"
  - "pytest 8.x FixtureFunctionDefinition.pytest_impl attribute inspected for hookimpl marker (not pytestmark)"
  - "src.utils.videos.VideoManager is the correct patch target for fixture-internal from-imports"
metrics:
  duration: "3m"
  completed: "2026-05-30"
  tasks_completed: 2
  tests_added: 20
  tests_total: 284
---

# Phase 12 Plan 02: pytest Integration Summary

## One-Liner

pytest_runtest_makereport hook + video_recorder fixture wired into conftest.py using StashKey to pass call-phase pass/fail outcome to fixture teardown for keep-or-delete decision.

## What Was Built

### tests/conftest.py (modified)

Three additions made:

**1. Import update:**
```python
from pytest import CollectReport, StashKey
```

**2. StashKey constant and hook (before CLI options section):**
```python
_phase_report_key: StashKey[dict[str, CollectReport]] = StashKey()

@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    rep = yield
    item.stash.setdefault(_phase_report_key, {})[rep.when] = rep
    return rep
```

**3. video_recorder fixture (after driver fixture):**
- `scope="function"`, parameters `(request, app_config, driver)`, no autouse
- Calls `VideoManager().start(name, headless=app_config.headless or not app_config.record_video)`
- Teardown reads `request.node.stash.get(_phase_report_key, {})` for call + setup reports
- `_Pass` sentinel handles case where stash is absent (error before call phase)
- Deletes video on pass; retains on fail; always calls `manager.stop()`

### tests/unit/test_conftest_hook.py (new)

6 tests verifying:
- `_phase_report_key` exists and is a `StashKey` instance
- `pytest_runtest_makereport` exists and is callable
- Hook has `pytest_impl` marker with `wrapper=True, tryfirst=True` options
- Hook uses `wrapper=True` not deprecated `hookwrapper=True`

### tests/unit/test_conftest_video_recorder.py (new)

14 tests verifying:
- Fixture presence, callability, opt-in (not autouse), function scope
- Signature has `request`, `app_config`, `driver` parameters
- Behavioral tests via `__wrapped__` raw generator:
  - `headless=True` → `start()` called with `headless=True`
  - `stop()` always called (even when video_path is None)
  - `delete()` called on test pass
  - `delete()` not called on test fail
  - No delete when `video_path is None`
  - Missing stash handled gracefully (no exception)
  - Setup failure treated same as call failure

## TDD Gate Compliance

### Task 1 (StashKey + hook)
- RED: commit `e01d783` — 6 failing tests for _phase_report_key and pytest_runtest_makereport
- GREEN: commit `efa826f` — implementation, all 6 pass

### Task 2 (video_recorder fixture)
- RED: commit `81097be` — 14 failing tests for video_recorder
- GREEN: commit `5c3bd2c` — implementation, all 14 pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed hookimpl marker attribute name in test**
- **Found during:** Task 1 GREEN phase — test_hook_has_hookimpl_marker failing
- **Issue:** Test checked `hook.pytestmark`, `hook.hookwrapper`, `hook._pytestwrap` — none exist. pytest 8.x stores hookimpl options in `hook.pytest_impl` dict (e.g., `{"wrapper": True, "tryfirst": True, ...}`)
- **Fix:** Updated assertion to check `hook.pytest_impl["wrapper"]` and `hook.pytest_impl["tryfirst"]`
- **Files modified:** `tests/unit/test_conftest_hook.py`
- **Commit:** Included in `efa826f`

**2. [Rule 1 - Bug] Fixed pytest 8.x fixture direct-call prohibition in behavior tests**
- **Found during:** Task 2 GREEN phase — all behavioral tests failing with "Fixture called directly"
- **Issue:** pytest 8.x wraps fixtures in `FixtureFunctionDefinition` which raises an error if the fixture is called directly. Tests originally used `conftest.video_recorder(request, ...)` pattern.
- **Fix:** Changed to use `conftest.video_recorder.__wrapped__(request, ...)` — the `__wrapped__` attribute exposes the raw generator function, bypassing the fixture framework enforcement.
- **Files modified:** `tests/unit/test_conftest_video_recorder.py`
- **Commit:** Included in `5c3bd2c`

**3. [Rule 1 - Bug] Fixed patch target for VideoManager in behavior tests**
- **Found during:** Task 2 GREEN phase — tests failing with AttributeError on patch target
- **Issue:** Tests patched `tests.conftest.VideoManager` but the fixture imports VideoManager inside the function body (`from src.utils.videos import VideoManager`), so the name is not in the conftest module's namespace. The correct target is `src.utils.videos.VideoManager`.
- **Fix:** Changed all patch targets to `src.utils.videos.VideoManager`
- **Files modified:** `tests/unit/test_conftest_video_recorder.py`
- **Commit:** Included in `5c3bd2c`

## Known Stubs

None. All interfaces are fully implemented and wired.

## Threat Flags

No new security surface beyond what is documented in the plan's threat model (T-12-05, T-12-06). T-12-06 mitigation implemented: `_Pass` sentinel handles missing stash gracefully and `manager.stop()` is always called.

## Self-Check

### Files Exist
- [x] `tests/conftest.py` — modified with StashKey, hook, video_recorder fixture
- [x] `tests/unit/test_conftest_hook.py` — created
- [x] `tests/unit/test_conftest_video_recorder.py` — created

### Commits Exist
- [x] `e01d783` — test RED: StashKey + hook tests
- [x] `efa826f` — feat GREEN: StashKey + hook implementation
- [x] `81097be` — test RED: video_recorder fixture tests
- [x] `5c3bd2c` — feat GREEN: video_recorder fixture implementation

### Test Results
- 284 unit tests pass (264 pre-existing + 20 new)
- No regressions

## Self-Check: PASSED
