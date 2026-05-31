# Phase 15: Add per-file coverage source drilldown - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the coverage reporting stack with three additions on top of Phase 14's baseline:
1. **Branch coverage** — enable `branch=true` in `.coveragerc` so both sides of every conditional are tracked and the per-file HTML pages show partial branches in yellow.
2. **Custom package-grouped index** — generate `reports/coverage/custom_index.html` after every pytest run: files organized by `src/` package with aggregate coverage %, branch coverage columns (Stmts | Miss | Branch | BrPart | Cover%), and links to the existing per-file `z_*.html` pages.
3. **Link from pytest HTML test report** — each test row in the Phase 13 `reports/*.html` report gets a test-level link to `coverage/index.html` (relative path), so developers can jump from test results to the coverage report.

Additionally, coverage is made opt-out: `--no-cov` (pytest-cov built-in flag, already available) can be passed to disable both coverage.py HTML generation and custom_index.html generation in a single run.

</domain>

<decisions>
## Implementation Decisions

### Branch Coverage
- **D-01:** Enable branch coverage — add `branch = true` under `[run]` in `.coveragerc`. Coverage.py will track whether both branches of every conditional (if/else, loop conditions) were executed.
- **D-02:** Per-file HTML pages (`z_*.html`) will automatically show partial branches in yellow (coverage.py handles this with no code changes once `branch = true` is set).
- **D-03:** The custom index page will include branch coverage columns: Stmts | Miss | Branch | BrPart | Cover%.

### Custom Index Page
- **D-04:** Generate `reports/coverage/custom_index.html` — sits alongside coverage.py's `index.html` in the same directory. Zero disruption to coverage.py's own output.
- **D-05:** Layout: grouped by package (core/, actions/, models/, etc. matching the `src/` subpackages). Each package section is a collapsible group (HTML `<details>/<summary>` — no JavaScript required, consistent with Phase 13 pattern) showing aggregate coverage % for the package. Files link to the existing `z_*.html` per-file pages.
- **D-06:** Reference coverage.py's generated CSS file (`style_cb_*.css`) by discovering its filename dynamically from the `reports/coverage/` directory. Visual consistency with the per-file pages. No extra styling to maintain.
- **D-07:** Columns per file row: File | Stmts | Miss | Branch | BrPart | Cover%.

### Integration with pytest HTML Test Report
- **D-08:** Each test row in the Phase 13 pytest HTML report gets a test-level link to `coverage/index.html`. The link uses a **relative path** from `reports/` (i.e., `coverage/index.html`), consistent with Phase 13's pattern for screenshots and videos.
- **D-09:** The link label should be "Coverage" or similar. It appears in the test row extras (same mechanism Phase 13 uses for step tables) — not a per-step link. Does not require mapping test → source files.
- **D-10:** Link is only rendered when `reports/coverage/index.html` exists (i.e., coverage ran on this session). If `--no-cov` was passed, no link appears.

### Coverage Flag (Opt-Out)
- **D-11:** Coverage is opt-out via pytest-cov's built-in `--no-cov` flag (already supported by pytest-cov). No custom flag needed. When `--no-cov` is passed, both coverage.py HTML and custom_index.html generation are skipped, and no coverage link appears in the pytest test report.
- **D-12:** The default behavior (always-on via `addopts`) is preserved. `--no-cov` is the escape hatch for quick runs.

### Generation Mechanism
- **D-13:** Wire a `pytest_sessionfinish` hook in `conftest.py` (or a new plugin module) that reads the generated coverage data and writes `custom_index.html` after coverage.py finishes. Same lifecycle as existing coverage generation — happens automatically on every pytest run (unless `--no-cov`).
- **D-14:** Read coverage data from the `.coverage` binary data file via the `coverage` Python API (`coverage.Coverage`, `coverage.CoverageData`) — not by scraping the generated HTML. This gives direct access to branch data, line data, and file paths.

### Claude's Discretion
- Exact hook/fixture for detecting `--no-cov` state: check `config.option.no_cov` (pytest-cov sets this) or presence of `--no-cov` in `config.invocation_params.args`.
- CSS filename discovery: glob for `style_cb_*.css` in `reports/coverage/` and use the first match, or read coverage.py's `status.json` if it exposes the filename.
- Package grouping logic: derive package name from file path (`src/actions/` → `actions`, etc.) by stripping `src/` prefix and using the first path component.
- Unit tests: cover the custom index generation logic (data parsing, HTML structure, package grouping) against a mock `.coverage` data set — not against the full coverage.py pipeline.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 14 baseline (must extend, not replace)
- `.planning/phases/14-add-python-unit-test-coverage-and-report/14-CONTEXT.md` — Decisions D-01 through D-09 are the Phase 14 baseline. Phase 15 extends them. Key: `branch = false` in Phase 14 (now changing to `true`), `pytest.ini` addopts pattern, `.coveragerc` format.
- `.coveragerc` — current `[run]` and `[html]` sections. Phase 15 adds `branch = true` under `[run]`.
- `pytest.ini` — current `addopts`. No changes to addopts in Phase 15 (--no-cov is already supported by pytest-cov without addopts change).

### Phase 13 integration patterns (link mechanism)
- `.planning/phases/13-generate-html-test-report/13-CONTEXT.md` — D-05 through D-07 describe the extras/artifact linking pattern. Phase 15 adds a "Coverage" link using the same extras mechanism.
- `tests/conftest.py` — `pytest_runtest_makereport` hook and stash pattern. Phase 15 hooks into the same `pytest_sessionfinish` lifecycle.
- `src/core/constants.py` — `SCREENSHOT_DIR`, `VIDEO_DIR`, `HTML_REPORT_DIR` constants; Phase 15 may add `COVERAGE_DIR = "reports/coverage"` or `CUSTOM_INDEX_FILENAME = "custom_index.html"`.

### Coverage.py API
- `coverage` Python package API (`coverage.Coverage`, `coverage.CoverageData`) — use to read `.coverage` data file for branch and line data. Do NOT scrape generated HTML.
- `reports/coverage/status.json` — generated by coverage.py; check if it exposes CSS filename or file metadata usable for custom_index generation.
- `reports/coverage/index.html` — existing coverage.py index; custom_index.html is a supplement, not a replacement.

### No external specs
- No external ADRs beyond the files listed above. Requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py` — `pytest_runtest_makereport` hook already wired; `pytest_sessionfinish` hook is the addition point for custom_index.html generation. Extend, don't replace.
- `src/utils/files.py` — `safe_filename`, `ensure_dir` utilities reusable for output path construction.
- Phase 13 extras mechanism — the `extras` list in `pytest_runtest_makereport` is the insertion point for the per-test "Coverage" link.
- `reports/coverage/` — already contains `style_cb_*.css`, `z_*.html` per-file pages, and `index.html` generated by coverage.py. `custom_index.html` joins this directory.

### Established Patterns
- All test artifacts under `reports/` subdirectory; relative paths for cross-artifact links.
- `<details>/<summary>` for collapsible sections (Phase 13 precedent — no JavaScript).
- Hook-based generation in `conftest.py` (Phases 12, 13 precedent).
- Constants in `src/core/constants.py` for directory names.

### Integration Points
- `tests/conftest.py` — add `pytest_sessionfinish` hook for custom_index.html generation; extend `pytest_runtest_makereport` extras to include coverage link.
- `.coveragerc` `[run]` section — add `branch = true`.
- `src/core/constants.py` — add coverage-related constants if needed.
- `reports/coverage/` — output directory for `custom_index.html`.

</code_context>

<specifics>
## Specific Ideas

- `custom_index.html` title: "Coverage Drilldown — [timestamp or run date]".
- Package sections use `<details open>` by default (all expanded) so low-coverage packages are immediately visible without clicking.
- Coverage % in the package header: show aggregate for the package in parentheses, e.g. `actions/ (78%)`.
- The "Coverage" link in the pytest test report extras: simple anchor `<a href="coverage/index.html">Coverage Report</a>`. The link points to coverage.py's own `index.html` (not `custom_index.html`) — the pytest report is the entry point for test results; the coverage index is the entry point for coverage. `custom_index.html` is discoverable from within the coverage directory.
- `.coverage` binary file stays in the project root (coverage.py default). Do not move it.

</specifics>

<deferred>
## Deferred Ideas

- **Minimum threshold enforcement** (`--cov-fail-under=N`) — deferred from Phase 14, still out of scope for Phase 15. Add after baseline branch coverage % is known.
- **XML report** (`coverage.xml`) for CI tools — still out of scope.
- **Coverage badge** in README — still deferred.
- **Per-test source file mapping** — linking each test row to the specific per-file `z_*.html` page for the source files that test exercises. Complex (requires `.coverage` test-to-file mapping). Deferred; Phase 15 uses a test-level link to the index instead.
- **Auto-cleanup** of old `.coverage` files — out of scope.

</deferred>

---

*Phase: 15-add-per-file-coverage-source-drilldown*
*Context gathered: 2026-05-31*
