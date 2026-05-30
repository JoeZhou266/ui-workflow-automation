# Phase 13: Generate HTML Test Report - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate an HTML test report after every pytest run. The report covers two levels:
1. **pytest test summary** — which test functions passed/failed/skipped, total duration, error messages
2. **Workflow step drill-down** — per-test expandable section showing the full Tab→Page→Section→Element execution chain from `ResultCollector`, with PASSED/FAILED/SKIPPED status, action type, duration, error message, and failure phase for each step

Reports are saved to `reports/` as timestamped HTML files named `<workflow_name>_report_<YYYYMMDD_HHMMSS>.html`.

</domain>

<decisions>
## Implementation Decisions

### Report Coverage
- **D-01:** Report shows **both levels**: pytest test-level summary (header/summary table) AND per-test workflow step detail (expandable drill-down from `ResultCollector.summary()`).
- **D-02:** Per-test drill-down shows **all steps** with status — PASSED (green), FAILED (red), SKIPPED (yellow) — including Tab→Page→Section→Element hierarchy, action type, and `duration_ms`. On FAILED steps: also show `error_message` and `failure_phase`.

### Library
- **D-03:** Use **pytest-html** (already installed at 4.2.0) as the base report generator. Extend it via pytest-html plugin hooks (`pytest_html_results_table_row`, `extras`) to inject the per-test workflow step details as an expandable section in each test row.
- **D-04:** Do NOT use Allure for this phase. Allure requires a separate server to view reports and is higher operational overhead for the local-dev use case.

### Artifact Embedding (Phase 12 Integration)
- **D-05:** Screenshots from `reports/screenshots/` are shown as **clickable linked thumbnails** on FAILED steps where `screenshot_path` is present on the `StepResult`. Use relative paths (e.g. `screenshots/20260530_143022_test_foo.png`) so links resolve when the HTML and `screenshots/` folder are in the same `reports/` directory.
- **D-06:** Videos from `reports/videos/` are shown as **linked filenames** (not embedded) on FAILED tests where a video path is available. Relative paths from `reports/`.
- **D-07:** Both artifact links appear only where the artifact actually exists — no broken links for tests that didn't capture a screenshot or video.

### Report Trigger
- **D-08:** Report is **always auto-generated** on every pytest run. Configure via `--html` and `--self-contained-html` flags added to `addopts` in `pytest.ini` (or via `conftest.py` hook). No opt-in flag required.

### Report Naming
- **D-09:** **Timestamped per run**, flat in `reports/`. Format: `<workflow_name>_report_<YYYYMMDD_HHMMSS>.html` (e.g. `sample_workflow_report_20260530_143022.html`). When no specific workflow name is available (full test suite run), use `run` as the prefix: `run_report_20260530_143022.html`.
- **D-10:** Files accumulate in `reports/` — no auto-cleanup. Matches the existing pattern (screenshots and videos also accumulate).

### Claude's Discretion
- Where exactly to hook into pytest-html's plugin API (exact hook names, extras format) — researcher should verify against pytest-html 4.2 docs.
- How `ResultCollector.summary()` is passed to the conftest hook — via fixture, stash, or direct import of a module-level collector. Follow existing `_phase_report_key` stash pattern in `conftest.py`.
- `.gitignore` update: add `reports/*.html` (keep `reports/.gitkeep`). Reports are generated artifacts, not committed.
- Unit tests: cover the report generation logic (not the full HTML output, but the data transformation from `ExecutionSummary` to the extras structure).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing patterns to mirror
- `src/workflow/result_collector.py` — `ResultCollector` class; `summary()` returns `ExecutionSummary` with `steps: List[StepResult]`, `total`, `passed`, `failed`, `skipped`, `start_time`, `end_time`
- `src/models/element_models.py` — `StepResult` and `ExecutionSummary` Pydantic models; check field names for `tab_name`, `page_name`, `section_name`, `element_name`, `action`, `status`, `error_message`, `failure_phase`, `screenshot_path`, `duration_ms`
- `tests/conftest.py` — `_phase_report_key` stash pattern for passing data from hook to fixture; `pytest_runtest_makereport` hook implementation; `video_recorder` fixture as integration point reference
- `src/utils/screenshots.py` — `ScreenshotManager` pattern (constructor, path conventions); artifact path format to match in relative link generation
- `src/core/constants.py` — existing `SCREENSHOT_DIR`, `VIDEO_DIR` constants; add `REPORT_DIR = "reports"` or `HTML_REPORT_DIR` here
- `src/core/config.py` — `AppConfig` YAML config pattern; check if `videos_dir` was added in Phase 12 for reference

### Config files to update
- `pytest.ini` — add `--html` and `--self-contained-html` (or dynamic path) to `addopts`; verify pytest-html 4.2 addopts syntax
- `.gitignore` — add `reports/*.html` to exclude generated HTML reports from version control

### Phase 12 deferred item being addressed
- `.planning/phases/12-support-video-capture/12-CONTEXT.md` — deferred section explicitly notes "HTML report embedding — embed videos in a test results HTML page; separate phase" — this phase fulfills that deferred item

### External docs
- pytest-html 4.2 plugin hooks — verify exact hook names: likely `pytest_html_results_table_row` and `extras` API. Researcher should check https://pytest-html.readthedocs.io for 4.x hook API (breaking changes from 3.x)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ResultCollector.summary()` → `ExecutionSummary`: ready-made data source for the step-level drill-down. Already called in `workflow_engine.py` at end of run.
- `StepResult` model: has all fields needed — `tab_name`, `page_name`, `section_name`, `element_name`, `action`, `status`, `error_message`, `failure_phase`, `screenshot_path`, `duration_ms`.
- `_phase_report_key` stash in `conftest.py`: established pattern for passing per-test data between hook and fixture. Report extras can follow the same pattern.
- `src/utils/files.py` (`safe_filename`, `ensure_dir`): reuse for report filename construction and directory creation.

### Established Patterns
- Failure artifacts go in `reports/<type>/` subdirectory with `<timestamp>_<safe_name>.<ext>` naming.
- `pytest_runtest_makereport` hook already wired in `conftest.py` — extend it (don't replace it) to also attach report extras.
- `AppConfig` YAML config for feature flags — not needed here since report is always auto-generated.

### Integration Points
- `tests/conftest.py`: attach `extras` to each test item in `pytest_runtest_makereport` or a new `pytest_html_results_table_row` hook. The `ResultCollector` for the test must be accessible here.
- `pytest.ini` `addopts`: add `--html` flag for auto-generation on every run.
- `src/core/constants.py`: add `HTML_REPORT_DIR` or reuse/extend existing `REPORT_DIR` constant.
- `.gitignore`: add `reports/*.html`.

</code_context>

<specifics>
## Specific Ideas

- Report filename: `<safe_workflow_name>_report_<YYYYMMDD_HHMMSS>.html`. The workflow name comes from the `--workflow` pytest option (extracted from the JSON filename). For runs without `--workflow`, use `run` prefix.
- pytest-html 4.x changed its plugin API significantly from 3.x — researcher must verify current hook names. The `extras` object and `pytest_html_results_table_row` hook may have different signatures.
- The step drill-down HTML in the extras should be a collapsible `<details>/<summary>` block (no JavaScript dependency) showing a table of steps. Each FAILED row highlights in red with error message below; each SKIPPED row in yellow; PASSED rows in green (or muted/no color for readability at scale).
- Screenshot thumbnails: small inline `<img>` (max 200px wide) wrapped in `<a href="...">` pointing to the relative path. Only rendered if `step.screenshot_path` is not None.
- Video link: `<a href="../videos/<filename>">▶ Video</a>` on the test row (not per-step).

</specifics>

<deferred>
## Deferred Ideas

- **Latest symlink** (`reports/report.html` → latest timestamped file) — mentioned but not chosen. Could be added later as a convenience.
- **Allure report** — installed but not used here. Could be activated for CI reporting in a future phase.
- **Report auto-cleanup** (keep last N reports) — same pattern deferred in Phase 12 for videos. Out of scope.
- **Base64 screenshot embedding** for fully portable self-contained HTML — noted as an option but deferred in favor of linked paths.
- **JSON export alongside HTML** — `ExecutionSummary` is Pydantic; a JSON export would be trivial but is out of scope for this phase.

</deferred>

---

*Phase: 13-generate-html-test-report*
*Context gathered: 2026-05-30*
