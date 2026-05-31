# Phase 15: Add Per-File Coverage Source Drilldown — Research

**Researched:** 2026-05-31
**Domain:** coverage.py Python API, pytest hooks, HTML generation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Enable branch coverage — add `branch = true` under `[run]` in `.coveragerc`.
- **D-02:** Per-file HTML pages (`z_*.html`) will automatically show partial branches in yellow (no code changes once `branch = true` is set).
- **D-03:** The custom index page will include branch coverage columns: Stmts | Miss | Branch | BrPart | Cover%.
- **D-04:** Generate `reports/coverage/custom_index.html` — sits alongside coverage.py's `index.html`. Zero disruption to coverage.py's own output.
- **D-05:** Layout: grouped by package (core/, actions/, models/, etc.). Each package section uses `<details open>` (collapsible, expanded by default, no JS). Files link to existing `z_*.html` per-file pages.
- **D-06:** Reference coverage.py's generated CSS file (`style_cb_*.css`) by discovering its filename dynamically. Visual consistency with per-file pages.
- **D-07:** Columns per file row: File | Stmts | Miss | Branch | BrPart | Cover%.
- **D-08:** Each test row in the pytest HTML report gets a test-level link to `coverage/index.html` (relative path `coverage/index.html`). Uses existing Phase 13 extras mechanism.
- **D-09:** Link label: "Coverage" or similar. Appears in test row extras, not per-step. Does not require test-to-source mapping.
- **D-10:** Link is only rendered when `reports/coverage/index.html` exists.
- **D-11:** Coverage is opt-out via pytest-cov's built-in `--no-cov` flag. No custom flag needed.
- **D-12:** Default behavior (always-on via `addopts`) is preserved.
- **D-13:** Wire `pytest_sessionfinish` hook in `conftest.py` (or a new plugin module) to read coverage data and write `custom_index.html`. Happens after coverage HTML is generated.
- **D-14:** Read coverage data from `.coverage` binary via `coverage` Python API — not by scraping HTML.

### Claude's Discretion

- Exact hook/fixture for detecting `--no-cov` state: check `config.option.no_cov` (pytest-cov stores it there) or presence of `--no-cov` in `config.invocation_params.args`.
- CSS filename discovery: glob for `style_cb_*.css` in `reports/coverage/` and use the first match, or read `status.json` if it exposes the filename.
- Package grouping logic: derive package name from file path (`src/actions/` → `actions`, etc.) by stripping `src/` prefix and using the first path component.
- Unit tests: cover the custom index generation logic (data parsing, HTML structure, package grouping) against a mock `.coverage` data set — not against the full coverage.py pipeline.

### Deferred Ideas (OUT OF SCOPE)

- Minimum threshold enforcement (`--cov-fail-under=N`)
- XML report (`coverage.xml`) for CI tools
- Coverage badge in README
- Per-test source file mapping (complex `.coverage` test-to-file mapping)
- Auto-cleanup of old `.coverage` files
</user_constraints>

---

## Summary

Phase 15 extends the Phase 14 coverage baseline with four concrete deliverables: (1) branch tracking in `.coveragerc`, (2) a custom package-grouped HTML index (`reports/coverage/custom_index.html`), (3) a per-test "Coverage" link in the Phase 13 pytest HTML report, and (4) implicit opt-out via `--no-cov`. All research was performed against the live project (coverage.py 7.10.7, pytest-cov 7.1.0, Python 3.9).

The central technical choice is the data source for generating `custom_index.html`. Research confirms that `coverage.py`'s `Coverage` Python API combined with `coverage.files.flat_rootname()` provides everything needed: line counts, branch counts, and the `z_*.html` filename for each source file. This approach avoids relying on `status.json` (documented as "internal implementation detail, format can change at any time") and avoids re-running a report subcommand.

Hook lifecycle ordering is confirmed safe: pytest-cov wraps `pytest_runtestloop` (not `pytest_sessionfinish`) to write coverage HTML. Our `pytest_sessionfinish` therefore always runs after the HTML report directory exists, making `.coverage` data and `reports/coverage/style_cb_*.css` available for reading.

**Primary recommendation:** Implement `custom_index.html` generation as a `pytest_sessionfinish` hook in `conftest.py`, using the `Coverage` Python API (`Coverage.load()` + `_analyze()`) and `flat_rootname()` for URL derivation. Extract the CSS filename via `glob.glob('reports/coverage/style_cb_*.css')`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Branch coverage tracking | `.coveragerc` config | coverage.py runtime | Single config line; coverage.py handles all instrumentation |
| Custom index HTML generation | `tests/conftest.py` hook | `src/utils/coverage_index.py` | Hook runs post-session; generation logic extracted for testability |
| Per-test coverage link | `tests/conftest.py` `pytest_runtest_makereport` | — | Existing extras mechanism already wired here |
| Coverage constants | `src/core/constants.py` | — | Mirror established SCREENSHOT_DIR/VIDEO_DIR pattern |
| CSS discovery | `src/utils/coverage_index.py` | — | Isolated glob logic, mockable in unit tests |
| `.coverage` data reading | `src/utils/coverage_index.py` | — | Uses `coverage` Python API; isolated for testability |

---

## Standard Stack

### Core (all already installed)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| coverage | 7.10.7 | `.coverage` data reading, `_analyze()`, branch stats | [VERIFIED: `python3 -c "import coverage; print(coverage.__version__)"`] |
| pytest-cov | 7.1.0 | `--no-cov` flag, `addopts` integration | [VERIFIED: `python3 -c "import pytest_cov; print(pytest_cov.__version__)"`] |
| coverage.files.flat_rootname | (part of coverage 7.10.7) | Derive `z_*.html` filename from source file path | [VERIFIED: roundtrip tested against live `reports/coverage/`] |

**No new dependencies.** All required libraries are already in `requirements.txt`.

---

## Technical Approach

### Deliverable 1: Branch Coverage (.coveragerc)

Single line addition under `[run]`:

```ini
[run]
source = src
omit =
    src/**/__init__.py
branch = true
```

Once `branch = true` is set, coverage.py collects arc data (branch transitions). The per-file `z_*.html` pages automatically show partial branches in yellow — no code changes required. [VERIFIED: coverage.py source confirms arc collection is config-driven; `coverage.CoverageData.has_arcs()` returns `True` only when branch data was collected.]

### Deliverable 2: custom_index.html Generation

**Data pipeline** (all calls verified live against project's `.coverage`):

```python
import os
import glob
from collections import defaultdict
from pathlib import Path

import coverage
from coverage.files import flat_rootname

def build_custom_index(
    coverage_dir: str = "reports/coverage",
    data_file: str = ".coverage",
) -> str:
    """Read .coverage, return HTML string for custom_index.html."""
    cov = coverage.Coverage(data_file=data_file)
    cov.load()
    data = cov.get_data()

    # CSS filename discovery — verified glob works against live reports/coverage/
    css_files = glob.glob(os.path.join(coverage_dir, "style_cb_*.css"))
    css_href = os.path.basename(css_files[0]) if css_files else ""

    # Group files by src/ package
    packages: dict[str, list[dict]] = defaultdict(list)
    for abs_path in sorted(data.measured_files()):
        rel = os.path.relpath(abs_path)          # e.g., "src/actions/action_factory.py"
        parts = rel.replace("\\", "/").split("/")
        pkg = parts[1] if len(parts) > 2 else "root"  # "actions", "core", etc.

        analysis = cov._analyze(abs_path)
        nums = analysis.numbers
        url = flat_rootname(rel) + ".html"       # e.g., "z_53726e404e20fec7_action_factory_py.html"

        packages[pkg].append({
            "rel": rel,
            "name": parts[-1],                   # "action_factory.py"
            "url": url,
            "stmts": nums.n_statements,
            "miss": nums.n_missing,
            "branch": nums.n_branches,
            "brpart": nums.n_partial_branches,
            "pct": round(nums.pc_covered),
        })

    return _render_html(packages, css_href)
```

**URL derivation is stable:** `flat_rootname()` is part of the public `coverage.files` module and deterministic given the relative file path. Verified that `flat_rootname("src/actions/action_factory.py")` produces `"z_53726e404e20fec7_action_factory_py"`, matching the actual filename in `reports/coverage/`. [VERIFIED: live test]

**Branch columns show 0 when branch=false:** Before `branch = true` is enabled, `nums.n_branches == 0` and `nums.n_partial_branches == 0`. Columns should still render (show "0" or "—") to avoid a regression when the index is first generated without branch data; after enabling branch, they populate naturally.

### Deliverable 3: Per-Test Coverage Link

The existing `pytest_runtest_makereport` hook in `tests/conftest.py` already appends `extras` on the teardown phase. Add a conditional link:

```python
# In pytest_runtest_makereport, teardown phase, after existing html_parts:
coverage_index = Path(HTML_REPORT_DIR) / "coverage" / "index.html"
if coverage_index.exists():
    html_parts.append(
        '<p><a href="coverage/index.html" target="_blank">Coverage Report</a></p>'
    )
```

**Relative path:** The pytest HTML report lives in `reports/` (e.g., `reports/run_report_*.html`). The coverage index lives in `reports/coverage/index.html`. Relative path from `reports/` is `coverage/index.html`. [VERIFIED: matches established `videos/` relative path pattern used for video links.]

**Condition:** Only emit the link when `reports/coverage/index.html` physically exists. This handles `--no-cov` runs automatically (the file won't exist or will be stale). [Decision D-10]

### Deliverable 4: --no-cov Detection in pytest_sessionfinish

The `pytest_sessionfinish` hook must skip `custom_index.html` generation when coverage is disabled:

```python
def pytest_sessionfinish(session, exitstatus):
    config = session.config
    no_cov = getattr(config.option, "no_cov", False)
    if no_cov:
        return  # coverage disabled, skip custom index generation

    data_file = Path(".coverage")
    if not data_file.exists():
        return  # no data to read (e.g., collection-only run)

    # Generate custom_index.html ...
```

**Confirmed attribute name:** `config.option.no_cov` is the correct attribute. pytest-cov registers `--no-cov` via `group.addoption('--no-cov', action='store_true', default=False, ...)` with no explicit `dest=`, so argparse converts `--no-cov` → `no_cov`. The plugin itself checks `self.options.no_cov` (line 280 in `pytest_cov/plugin.py`). [VERIFIED: pytest-cov 7.1.0 source]

---

## coverage.py API Usage

All API calls verified against coverage.py 7.10.7 with the project's live `.coverage` file.

### Reading Line and Branch Stats

```python
import coverage
from coverage.files import flat_rootname
import os

cov = coverage.Coverage(data_file=".coverage")
cov.load()
data = cov.get_data()

# Check if branch data was collected
has_branches = data.has_arcs()  # True only when branch=true was active during collection

for abs_path in sorted(data.measured_files()):
    rel = os.path.relpath(abs_path)          # "src/actions/action_factory.py"
    analysis = cov._analyze(abs_path)
    nums = analysis.numbers

    # Line coverage
    n_statements = nums.n_statements         # Total executable statements
    n_missing = nums.n_missing               # Uncovered statements
    n_executed = nums.n_executed             # = n_statements - n_missing

    # Branch coverage (0 when branch=false in .coveragerc)
    n_branches = nums.n_branches             # Total branch transitions possible
    n_partial_branches = nums.n_partial_branches  # Branches only partially covered
    n_missing_branches = nums.n_missing_branches  # Uncovered branch transitions

    # Coverage percentage (0.0-100.0 float)
    pc_covered = nums.pc_covered             # e.g., 37.0
    pc_covered_str = nums.pc_covered_str     # e.g., "37"

    # URL of the per-file HTML page
    url = flat_rootname(rel) + ".html"       # "z_53726e404e20fec7_action_factory_py.html"
```

### Status of _analyze()

`Coverage._analyze()` is prefixed with `_` (internal), but it's been stable across coverage 5.x-7.x and is the pattern used by the HTML reporter itself internally. It returns an `Analysis` object with a `.numbers` attribute of type `Numbers` (a `dataclass`). This is preferable to scraping `status.json` (which carries an explicit "internal, can change" warning in the file itself).

**Risk:** If a future coverage.py major version renames `_analyze`, the code will raise `AttributeError`. Mitigate with a clear try/except that logs a warning and skips generation (fail-open: skip custom index, don't fail the test run).

### CSS Filename Discovery

```python
import glob
import os

coverage_dir = "reports/coverage"
css_files = glob.glob(os.path.join(coverage_dir, "style_cb_*.css"))
css_href = os.path.basename(css_files[0]) if css_files else ""
```

Verified: `reports/coverage/style_cb_6b508a39.css` exists after a standard `pytest` run. The hash suffix changes with coverage.py versions, not with test runs — so within a given coverage.py version the filename is stable, but across upgrades it may change. Dynamic glob discovery is correct. [VERIFIED: live filesystem check]

---

## Hook Integration

### Hook Lifecycle Ordering

```
pytest_runtestloop (wrapper) starts
  → tests run
  → (yield)
  → cov_controller.finish()    ← coverage.py writes .coverage + reports/coverage/
pytest_terminal_summary
pytest_sessionfinish            ← our hook: .coverage and reports/coverage/ already exist
```

Coverage HTML generation happens inside pytest-cov's `pytest_runtestloop` wrapper, **before** `pytest_sessionfinish` fires. [VERIFIED: pytest_cov/plugin.py lines 347-351 show `cov_controller.finish()` is called after `yield` in `pytest_runtestloop`.]

This ordering means `pytest_sessionfinish` can safely read `.coverage` and the `reports/coverage/` directory.

### Hook Signature

```python
def pytest_sessionfinish(session, exitstatus):
    """Generate custom_index.html after coverage HTML is written."""
    config = session.config
    no_cov = getattr(config.option, "no_cov", False)
    if no_cov:
        return

    data_file = Path(".coverage")
    if not data_file.exists():
        return

    try:
        html = build_custom_index()
        out = Path("reports/coverage/custom_index.html")
        out.write_text(html, encoding="utf-8")
    except Exception as exc:
        import warnings
        warnings.warn(f"coverage_index: failed to generate custom_index.html: {exc}")
```

**Fail-open design:** Any exception during generation should warn (not crash the pytest session). Coverage reporting is a developer convenience, not a correctness gate.

### Per-Test Link Detection in pytest_runtest_makereport

```python
# Existing teardown block in pytest_runtest_makereport:
if rep.when == "teardown":
    # ... existing html_parts building ...
    coverage_index = Path(HTML_REPORT_DIR) / "coverage" / "index.html"
    if coverage_index.exists():
        html_parts.append(
            '<p><a href="coverage/index.html" target="_blank">Coverage Report</a></p>'
        )
```

**Note on timing:** `pytest_runtest_makereport` fires during the test run, before `pytest_sessionfinish`. At teardown time, `reports/coverage/index.html` may not yet exist (coverage HTML is written in `runtestloop` after all tests complete). However, the `extras` list is only consumed by pytest-html when writing the final HTML report, which happens after all hooks complete. The `Path.exists()` check runs at hook time, so it will see the pre-existing `index.html` from the previous run (if any), or return False on first run. This is acceptable — the link appears for runs where coverage data exists from a previous run, and is absent on the very first run. [ASSUMED: this behavior is acceptable per D-10's intent]

**Alternative:** If the timing issue is unacceptable, use `pytest_sessionfinish` to add the coverage link by mutating the HTML report file after both coverage and test reports are written. However, this is significantly more complex and contradicts the established Phase 13 extras pattern. The user's D-10 says "link is only rendered when `reports/coverage/index.html` exists" — which the stale-check semantics satisfy.

---

## HTML Generation

### custom_index.html Structure

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Coverage Drilldown — {timestamp}</title>
  <link rel="stylesheet" href="{css_href}">  <!-- e.g., style_cb_6b508a39.css -->
</head>
<body>
  <h1>Coverage Drilldown — {timestamp}</h1>
  <p>Generated: {datetime} | Overall: {total_pct}%</p>

  <!-- Package section (one per src/ subdirectory) -->
  <details open>
    <summary><b>actions/ (78%)</b> — 3 files, 196 stmts</summary>
    <table>
      <thead>
        <tr>
          <th>File</th><th>Stmts</th><th>Miss</th>
          <th>Branch</th><th>BrPart</th><th>Cover%</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><a href="z_53726e404e20fec7_action_factory_py.html">src/actions/action_factory.py</a></td>
          <td>41</td><td>0</td><td>12</td><td>0</td><td>100%</td>
        </tr>
        <!-- ... -->
      </tbody>
    </table>
  </details>

  <!-- ... more packages ... -->
</body>
</html>
```

**Design choices:**
- `<details open>` (all expanded by default, per D-05 specifics): low-coverage packages immediately visible
- Package aggregate in `<summary>`: `actions/ (78%)` format
- File links point to `z_*.html` (relative — same directory as `custom_index.html`)
- CSS link to `style_cb_*.css` provides visual consistency with coverage.py pages
- No inline JS; no external CDN

### Package Grouping Logic

```python
def _package_from_path(rel_path: str) -> str:
    """Extract package name from relative file path.

    "src/actions/action_factory.py" -> "actions"
    "src/ui/pages/dynamic_page.py" -> "ui"
    """
    parts = rel_path.replace("\\", "/").split("/")
    # parts[0] == "src", parts[1] == package, parts[-1] == filename
    return parts[1] if len(parts) > 2 else "root"
```

**Verified package list** from live `.coverage` data:
`actions`, `core`, `data`, `driver`, `locators`, `models`, `ui`, `utils`, `waits`, `workflow` — all 10 subpackages. Files like `src/ui/pages/dynamic_page.py` and `src/ui/sections/dynamic_section.py` group under `ui` (not `pages`/`sections`), which is correct per the instruction "first path component after `src/`". [VERIFIED: live data test]

---

## Phase 13 Link Integration

### Existing Extras Mechanism (Phase 13 Pattern)

The existing `pytest_runtest_makereport` hook in `tests/conftest.py` (lines 66-80) already:
1. Builds `html_parts` list from workflow summary and video link
2. Joins to `html_str`
3. Appends `html_extras.html(html_str)` to `rep.extras`

Adding the coverage link is a single conditional append to `html_parts`:

```python
# After video_path block, before html_str join:
coverage_index = Path(HTML_REPORT_DIR) / "coverage" / "index.html"
if coverage_index.exists():
    html_parts.append(
        '<p><a href="coverage/index.html" target="_blank">Coverage Report</a></p>'
    )
```

**Import needed:** `from pathlib import Path` (already imported in conftest.py).

**No new stash keys needed.** The link is derived from filesystem state, not from per-test data.

---

## File Impact

### Files to Modify

| File | Change |
|------|--------|
| `.coveragerc` | Add `branch = true` under `[run]` |
| `tests/conftest.py` | (1) Add `pytest_sessionfinish` hook for `custom_index.html`; (2) Extend `pytest_runtest_makereport` teardown to append coverage link |
| `src/core/constants.py` | Add `COVERAGE_DIR = "reports/coverage"` constant (mirrors SCREENSHOT_DIR/VIDEO_DIR pattern) |

### Files to Create

| File | Purpose |
|------|---------|
| `src/utils/coverage_index.py` | `build_custom_index()` — pure function that reads `.coverage` and returns HTML string. Extracted from conftest for testability. |
| `tests/unit/test_coverage_index.py` | Unit tests for `build_custom_index()` and helpers using a mock `.coverage` dataset |
| `tests/unit/test_coverage_conftest.py` | Unit tests verifying `pytest_sessionfinish` hook presence and `--no-cov` detection |

### Files to NOT Modify

| File | Reason |
|------|--------|
| `pytest.ini` | `addopts` already has `--cov=src --cov-report=html:reports/coverage`. No changes needed. `--no-cov` is built into pytest-cov. |
| `requirements.txt` | All dependencies already present (coverage + pytest-cov) |
| `.gitignore` | `reports/coverage/` already gitignored |

---

## Risks and Pitfalls

### Pitfall 1: coverage._analyze() Is an Internal API

**What goes wrong:** `cov._analyze()` is prefixed with `_`. A future coverage.py major version could rename or remove it.

**Why it happens:** coverage.py doesn't expose a stable public API for per-file stats at the Python object level. The documented public surface is `cov.report()`, `cov.html_report()`, `cov.json_report()` — all of which write to files/stdout, not return data objects.

**How to avoid:** Wrap the call in a `try/except AttributeError` + a broader `try/except Exception` that warns and skips generation (fail-open). The test run is never failed due to custom index generation errors.

**Alternative considered:** `cov.json_report(outfile=tmpfile)` writes a JSON file we could parse. When `has_arcs()` is True (branch=true), the JSON summary adds `num_branches`, `num_partial_branches`, `covered_branches`, `missing_branches`. [VERIFIED: `coverage/jsonreport.py` source, `make_branch_summary()` at line 55.] This is a documented public API but requires a tempfile roundtrip. `_analyze()` is simpler and is verified to be the same data source the HTML reporter uses.

**Recommendation:** Use `_analyze()` with the fail-open wrapper. Document the internal API risk in code comments.

### Pitfall 2: .coverage Does Not Exist (First Run Without Prior Data)

**What goes wrong:** `coverage.Coverage.load()` raises `coverage.exceptions.NoDataError` if `.coverage` is absent.

**Why it happens:** First-ever run, or run with `--no-cov`, or when tests are collected-only (`--collect-only`).

**How to avoid:** Check `Path(".coverage").exists()` before calling `cov.load()`. Return early if absent.

### Pitfall 3: CSS File Not Found After --no-cov Run

**What goes wrong:** `glob.glob('reports/coverage/style_cb_*.css')` returns empty list if the `reports/coverage/` directory doesn't exist yet (first run, or cleaned up).

**Why it happens:** `reports/coverage/` is populated by coverage.py's HTML report. If that report wasn't written, the directory may be empty or missing.

**How to avoid:** When `css_files` is empty, use `css_href = ""` and omit the `<link>` stylesheet tag. The page will lack styling but will be functional. The `pytest_sessionfinish` guard on `Path(".coverage").exists()` should prevent most of these cases, but the CSS glob should still handle the empty-list case.

### Pitfall 4: Coverage Link Always Shows Previous Run's Data

**What goes wrong:** The coverage link in pytest-html test rows is added during `pytest_runtest_makereport` (teardown phase), which fires before coverage HTML is written by `cov_controller.finish()`. The `Path.exists()` check sees the `index.html` from the *previous* run.

**Why it happens:** Hook ordering — runtestloop writes coverage HTML after all tests complete, but `pytest_runtest_makereport` runs during the test execution phase.

**Impact:** On the very first pytest run (no previous `reports/coverage/index.html`), no coverage link appears. On subsequent runs, the link always appears (pointing to coverage data from the *current* run, since coverage overwrites the same directory). For the typical developer workflow (not first run), this is correct behavior. [ASSUMED: acceptable per D-10's intent; "exists" check is sufficient]

**How to avoid (if needed):** Move link injection to `pytest_sessionfinish` by mutating the HTML report file. But this contradicts the established Phase 13 extras pattern and adds significant complexity. Recommend the simple check-and-link approach for now.

### Pitfall 5: Branch Columns Show 0 Until branch=true Takes Effect

**What goes wrong:** If developer runs tests immediately after adding `branch = true` to `.coveragerc` but before collecting fresh coverage data, `n_branches` is still 0.

**Why it happens:** `.coverage` binary file stores the collected data from the *last* run. The branch instrumentation only activates for new runs.

**Impact:** The `custom_index.html` Branch and BrPart columns will show 0 until the next `pytest` run after enabling `branch = true`. This is expected and documented behavior — the branch columns will populate on the first run with branch tracking enabled.

**How to avoid:** No code mitigation needed. Branch=0 is a valid state (means: data not yet collected). Show 0/— rather than hiding the column.

### Pitfall 6: Subpackage Files Group at Wrong Level

**What goes wrong:** `src/ui/pages/dynamic_page.py` could be grouped as `ui` (correct, per D-05) or as `pages` (wrong).

**How to avoid:** Use `parts[1]` (index of first path component after `src/`) as the package name. For `src/ui/pages/dynamic_page.py`, `parts = ['src', 'ui', 'pages', 'dynamic_page.py']`, so `parts[1] = 'ui'`. [VERIFIED: live test shows `ui` is correct grouping]

---

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | `pytest.ini` |
| Quick run command | `pytest tests/unit/test_coverage_index.py tests/unit/test_coverage_conftest.py -v --no-cov` |
| Full suite command | `pytest tests/unit/ -v` |

Note: Use `--no-cov` in the quick run command when running only coverage-related tests, to avoid generating a new `.coverage` file mid-test.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File |
|--------|----------|-----------|-------------------|------|
| COV-01 | `branch = true` in `.coveragerc` | unit (config parse) | `pytest tests/unit/test_coverage_index.py::TestCoverageRc -v --no-cov` | Wave 0 |
| COV-02 | `build_custom_index()` returns HTML with all 10 packages | unit | `pytest tests/unit/test_coverage_index.py::TestBuildCustomIndex -v --no-cov` | Wave 0 |
| COV-03 | Package grouping: `src/ui/pages/x.py` → `ui` | unit | `pytest tests/unit/test_coverage_index.py::TestPackageGrouping -v --no-cov` | Wave 0 |
| COV-04 | CSS glob returns correct `style_cb_*.css` href | unit | `pytest tests/unit/test_coverage_index.py::TestCssDiscovery -v --no-cov` | Wave 0 |
| COV-05 | `<details open>` present for each package group | unit | `pytest tests/unit/test_coverage_index.py::TestHtmlStructure -v --no-cov` | Wave 0 |
| COV-06 | File rows include all 6 columns (File, Stmts, Miss, Branch, BrPart, Cover%) | unit | `pytest tests/unit/test_coverage_index.py::TestHtmlStructure -v --no-cov` | Wave 0 |
| COV-07 | `pytest_sessionfinish` hook exists in conftest | unit | `pytest tests/unit/test_coverage_conftest.py::TestSessionFinishHook -v --no-cov` | Wave 0 |
| COV-08 | `--no-cov` detection: `config.option.no_cov` checked before generation | unit | `pytest tests/unit/test_coverage_conftest.py::TestNoCovDetection -v --no-cov` | Wave 0 |
| COV-09 | Coverage link in `pytest_runtest_makereport` teardown extras | unit | `pytest tests/unit/test_coverage_conftest.py::TestCoverageLinkExtras -v --no-cov` | Wave 0 |
| COV-10 | Missing `.coverage` file: generation skipped gracefully | unit | `pytest tests/unit/test_coverage_index.py::TestMissingCoverageFile -v --no-cov` | Wave 0 |
| COV-11 | `build_custom_index()` with empty CSS glob: no crash | unit | `pytest tests/unit/test_coverage_index.py::TestCssDiscovery -v --no-cov` | Wave 0 |

### Mock Strategy for Unit Tests

`build_custom_index()` must accept injectable dependencies for testability:

```python
def build_custom_index(
    coverage_dir: str = "reports/coverage",
    data_file: str = ".coverage",
    _cov_factory=None,   # override for testing: lambda data_file: MockCoverage()
) -> str:
```

Unit tests inject a mock `Coverage` object that returns deterministic `measured_files()` and `_analyze()` results without needing a real `.coverage` file.

### Wave 0 Gaps

- [ ] `tests/unit/test_coverage_index.py` — covers COV-01 through COV-06, COV-10, COV-11
- [ ] `tests/unit/test_coverage_conftest.py` — covers COV-07, COV-08, COV-09
- [ ] `src/utils/coverage_index.py` — the implementation to be tested

*(Existing test infrastructure covers all other unit tests — no conftest or framework changes needed.)*

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| z_*.html filename computation | Custom hash or glob of existing files | `coverage.files.flat_rootname(rel_path) + ".html"` | Coverage.py owns the hash algorithm; rolling your own will diverge |
| Branch stats extraction | Scraping z_*.html pages | `Coverage._analyze(file).numbers` | HTML is presentation; Numbers is the authoritative data model |
| Coverage option detection | Parsing `sys.argv` manually | `getattr(config.option, "no_cov", False)` | pytest-cov already normalizes this via argparse |
| Coverage HTML styling | Custom CSS | Linking to existing `style_cb_*.css` via glob | Zero maintenance; visual consistency with per-file pages |

---

## Code Examples

### complete build_custom_index() sketch

```python
# Source: verified against coverage.py 7.10.7, coverage.files source, live .coverage data
from __future__ import annotations

import glob
import os
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional

import coverage
from coverage.files import flat_rootname


def build_custom_index(
    coverage_dir: str = "reports/coverage",
    data_file: str = ".coverage",
) -> str:
    """Read .coverage binary and return HTML for reports/coverage/custom_index.html."""
    cov = coverage.Coverage(data_file=data_file)
    cov.load()
    data = cov.get_data()

    # CSS discovery
    css_files = glob.glob(os.path.join(coverage_dir, "style_cb_*.css"))
    css_href = os.path.basename(css_files[0]) if css_files else ""

    # Build package groups
    packages: dict[str, list[dict]] = defaultdict(list)
    total_stmts = total_miss = 0

    for abs_path in sorted(data.measured_files()):
        rel = os.path.relpath(abs_path)
        parts = rel.replace("\\", "/").split("/")
        pkg = parts[1] if len(parts) > 2 else "root"

        analysis = cov._analyze(abs_path)
        nums = analysis.numbers
        url = flat_rootname(rel) + ".html"

        packages[pkg].append({
            "rel": rel,
            "url": url,
            "stmts": nums.n_statements,
            "miss": nums.n_missing,
            "branch": nums.n_branches,
            "brpart": nums.n_partial_branches,
            "pct": round(nums.pc_covered),
        })
        total_stmts += nums.n_statements
        total_miss += nums.n_missing

    overall_pct = round((1 - total_miss / total_stmts) * 100) if total_stmts else 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return _render_html(packages, css_href, timestamp, overall_pct)


def _render_html(
    packages: dict,
    css_href: str,
    timestamp: str,
    overall_pct: int,
) -> str:
    css_link = f'<link rel="stylesheet" href="{escape(css_href)}">' if css_href else ""
    sections = "".join(_render_package(pkg, files) for pkg, files in sorted(packages.items()))
    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        f"<title>Coverage Drilldown — {timestamp}</title>"
        f"{css_link}"
        "</head><body>"
        f"<h1>Coverage Drilldown — {timestamp}</h1>"
        f"<p>Overall: {overall_pct}%</p>"
        f"{sections}"
        "</body></html>"
    )


def _render_package(pkg: str, files: list) -> str:
    pkg_stmts = sum(f["stmts"] for f in files)
    pkg_miss = sum(f["miss"] for f in files)
    pkg_pct = round((1 - pkg_miss / pkg_stmts) * 100) if pkg_stmts else 0
    rows = "".join(_render_row(f) for f in files)
    return (
        "<details open>"
        f"<summary><b>{escape(pkg)}/ ({pkg_pct}%)</b> — {len(files)} files, {pkg_stmts} stmts</summary>"
        "<table><thead><tr>"
        "<th>File</th><th>Stmts</th><th>Miss</th><th>Branch</th><th>BrPart</th><th>Cover%</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        "</details>"
    )


def _render_row(f: dict) -> str:
    return (
        "<tr>"
        f'<td><a href="{escape(f["url"])}">{escape(f["rel"])}</a></td>'
        f"<td>{f['stmts']}</td>"
        f"<td>{f['miss']}</td>"
        f"<td>{f['branch']}</td>"
        f"<td>{f['brpart']}</td>"
        f"<td>{f['pct']}%</td>"
        "</tr>"
    )
```

### pytest_sessionfinish hook

```python
# Source: pytest_cov/plugin.py (hook ordering verified)
def pytest_sessionfinish(session, exitstatus):
    """Generate custom_index.html after coverage HTML is written."""
    from pathlib import Path
    from src.utils.coverage_index import build_custom_index
    from src.core.constants import COVERAGE_DIR

    config = session.config
    if getattr(config.option, "no_cov", False):
        return

    if not Path(".coverage").exists():
        return

    try:
        html = build_custom_index(coverage_dir=COVERAGE_DIR)
        out = Path(COVERAGE_DIR) / "custom_index.html"
        out.write_text(html, encoding="utf-8")
    except Exception as exc:
        import warnings
        warnings.warn(f"coverage_index: {exc}")
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| coverage | custom_index generation | ✓ | 7.10.7 | — |
| pytest-cov | `--no-cov` flag, `addopts` | ✓ | 7.1.0 | — |
| coverage.files.flat_rootname | URL derivation | ✓ | (part of coverage 7.10.7) | — |
| glob (stdlib) | CSS discovery | ✓ | stdlib | — |
| pathlib (stdlib) | File I/O | ✓ | stdlib | — |

No missing dependencies. All available in the project's `.venv`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Coverage link `Path.exists()` check in `pytest_runtest_makereport` sees the previous run's `index.html` (not the current run's); this is acceptable behavior per D-10 | Phase 13 Link Integration | If unacceptable: requires moving link injection to `pytest_sessionfinish` (more complex) |
| A2 | `coverage._analyze()` remains stable in coverage.py 7.x and near-future 8.x | coverage.py API Usage | If renamed: `AttributeError` in `build_custom_index()`; caught by fail-open `except` |

---

## Sources

### Primary (HIGH confidence)

- `coverage.py 7.10.7` — installed in `.venv`; verified via `python3 -c "import coverage; print(coverage.__version__)"`. API calls confirmed: `Coverage.load()`, `get_data()`, `_analyze()`, `CoverageData.measured_files()`, `CoverageData.has_arcs()`, `Numbers` dataclass fields, `flat_rootname()`.
- `pytest_cov 7.1.0` — installed; verified via `python3 -c "import pytest_cov; print(pytest_cov.__version__)"`. Plugin source inspected for `--no-cov` handling (`addoption`, `options.no_cov`), hook lifecycle (`pytest_runtestloop` wrapper vs `pytest_sessionfinish`).
- `reports/coverage/` — live filesystem; verified CSS glob, `status.json` structure, `z_*.html` naming, `flat_rootname()` roundtrip.
- `tests/conftest.py` — project file; verified existing `pytest_runtest_makereport` extras mechanism (lines 66-80), existing imports, stash pattern.
- `coverage/jsonreport.py` — coverage.py source; verified `make_branch_summary()` fields: `num_branches`, `num_partial_branches`, `covered_branches`, `missing_branches` (added to JSON summary only when `has_arcs()` is True).

### Secondary (MEDIUM confidence)

- `_pytest.hookspec` — verified `pytest_sessionfinish(session, exitstatus)` signature.
- `coverage.files.flat_rootname` — source inspected; uses `sha3_256` of dirname as 16-hex prefix + `basename.replace(".", "_")`.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified against installed packages
- Architecture: HIGH — coverage.py source + pytest-cov source inspected
- Pitfalls: HIGH — derived from actual source code inspection, not assumed
- Hook ordering: HIGH — `pytest_runtestloop` wrapper confirmed as coverage write point

**Research date:** 2026-05-31
**Valid until:** 2026-08-31 (coverage.py and pytest-cov are stable; `_analyze()` internal API risk is low but documented)
