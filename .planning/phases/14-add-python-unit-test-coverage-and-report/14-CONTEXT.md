# Phase 14: Add Python unit test coverage and report in project - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Add code coverage measurement and HTML reporting to the project. Every `pytest` run will measure which source lines in `src/` are exercised by the test suite, print a per-file summary table to the terminal, and write a browsable HTML report to `reports/coverage/`. No minimum threshold enforcement — this phase is about visibility, not gating.

</domain>

<decisions>
## Implementation Decisions

### Coverage Library
- **D-01:** Use **pytest-cov** (wraps coverage.py). Add `pytest-cov` to `requirements.txt`. This is the standard pytest integration — no alternative considered.

### Coverage Scope
- **D-02:** Measure **all of `src/`** — all 9 subpackages included. Lines in browser-dependent modules (`src/driver/`, `src/ui/`) will appear as uncovered since unit tests don't spin up Selenium — this is the honest picture and is acceptable.
- **D-03:** Exclude **`__init__.py` files** from coverage measurement. These are re-exports only; excluding them raises the reported percentage without hiding real gaps.

### Report Format
- **D-04:** Generate **two formats on every run**:
  1. **Terminal summary** — per-file coverage % table printed to stdout after the test run.
  2. **HTML report** — full browsable report showing which lines are covered/uncovered.
- **D-05:** No XML report for this phase. CI tool integration (Codecov, SonarQube) is out of scope.

### Report Location
- **D-06:** HTML report goes to **`reports/coverage/`** — consistent with the established `reports/` convention for all artifacts (screenshots in `reports/screenshots/`, videos in `reports/videos/`, HTML test reports in `reports/*.html`).
- **D-07:** `.coveragerc` (or `[coverage:run]` in `setup.cfg`) configures `source = src`, `omit = src/**/__init__.py`, `html_dir = reports/coverage`.

### Run Mode
- **D-08:** Coverage runs **always** — wire `--cov=src --cov-report=term-missing --cov-report=html:reports/coverage` into `addopts` in `pytest.ini`. No opt-in flag required. Smoke tests are also measured (harmless, ~1-2s overhead).

### Minimum Threshold
- **D-09:** **No threshold enforcement** for this phase. The goal is visibility. A `--cov-fail-under` can be added in a later phase once the baseline is known.

### Claude's Discretion
- Coverage config file format: `.coveragerc` vs inline in `pytest.ini` — follow whichever minimizes `pytest.ini` line length.
- `.gitignore` update: add `reports/coverage/` to exclude the generated HTML tree.
- Unit tests: cover the `pytest.ini` / `.coveragerc` integration (a smoke check that `pytest --co` lists coverage options correctly) rather than writing tests for coverage itself.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing patterns to follow
- `pytest.ini` — current `addopts = -v --tb=short`; extend with `--cov=src --cov-report=term-missing --cov-report=html:reports/coverage`
- `requirements.txt` — add `pytest-cov>=4.0.0`; no `pyproject.toml` exists
- `.gitignore` — existing `reports/assets/` exclusion pattern; add `reports/coverage/` alongside it
- `src/core/constants.py` — check if `COVERAGE_DIR` constant is warranted (mirror `SCREENSHOT_DIR`, `VIDEO_DIR` pattern from Phases 12–13); likely not needed since coverage is configured via `.coveragerc`/`pytest.ini`, not runtime Python

### Phase 12 & 13 artifact conventions
- `.planning/phases/12-support-video-capture/12-CONTEXT.md` — `reports/videos/` convention
- `.planning/phases/13-generate-html-test-report/13-CONTEXT.md` — `reports/*.html` and `reports/assets/` convention

### External docs
- pytest-cov docs: https://pytest-cov.readthedocs.io — verify `--cov-report=html:<dir>` syntax for current version
- coverage.py `.coveragerc` format: https://coverage.readthedocs.io/en/latest/config.html — `[run]` section for `source`, `omit`; `[html]` section for `directory`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pytest.ini` `addopts` line — extend, don't replace. Current: `-v --tb=short`.
- `.gitignore` — existing `reports/assets/` exclusion is the direct model for `reports/coverage/`.
- `requirements.txt` — single flat file, add `pytest-cov>=4.0.0`.

### Established Patterns
- All test artifacts go under `reports/` with a subdirectory per artifact type.
- `pytest.ini` `addopts` is how always-on pytest behavior is configured in this project (Phase 13 used it for `--html` flag).
- No `pyproject.toml` or `setup.cfg` — use `.coveragerc` for coverage-specific config if it keeps `pytest.ini` clean.

### Integration Points
- `pytest.ini` `addopts`: add `--cov=src --cov-report=term-missing --cov-report=html:reports/coverage`
- `requirements.txt`: add `pytest-cov>=4.0.0`
- `.coveragerc` (new file): `[run] source = src`, `omit = src/**/__init__.py`; `[html] directory = reports/coverage`
- `.gitignore`: add `reports/coverage/`

</code_context>

<specifics>
## Specific Ideas

- Terminal report should use `term-missing` (not just `term`) so uncovered line numbers are visible inline without opening the HTML.
- HTML report is always regenerated on every run — no timestamping needed (unlike HTML test reports from Phase 13). Coverage tracks the codebase state, not a specific test run moment.
- The `reports/coverage/` directory will contain `index.html` plus one file per source module — the whole subtree is gitignored.
- If pytest-cov conflicts with the Phase 13 `--html` flag (both write to `reports/`), they are independent outputs and should not conflict.

</specifics>

<deferred>
## Deferred Ideas

- **Minimum threshold enforcement** (`--cov-fail-under=N`) — deferred until a baseline coverage % is known after the first run.
- **XML report** (`coverage.xml`) for CI tools (Codecov, SonarQube) — out of scope for this phase.
- **Coverage badge** in README — requires CI integration, deferred.
- **Branch coverage** (`branch = true` in `.coveragerc`) — measures whether both sides of conditionals are tested; more thorough but higher noise. Deferred.
- **Per-run timestamped HTML** — Phase 13 does this for test reports; coverage HTML overwrites each run by design (shows current state, not history).

</deferred>

---

*Phase: 14-add-python-unit-test-coverage-and-report*
*Context gathered: 2026-05-30*
