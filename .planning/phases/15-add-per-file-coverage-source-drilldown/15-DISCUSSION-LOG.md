# Phase 15: Add per-file coverage source drilldown - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 15-add-per-file-coverage-source-drilldown
**Areas discussed:** Scope of drilldown, Integration with pytest report, Branch coverage data, Custom index vs coverage.py default, Add parameter for enable code coverage in pytest

---

## Scope of drilldown

| Option | Description | Selected |
|--------|-------------|----------|
| Link from pytest report | The gap is that the pytest HTML test report (Phase 13) doesn't link to the per-file coverage pages. | |
| Richer coverage metrics | Add branch coverage, missed instructions, or other JaCoCo-style columns. | |
| Custom per-file index | Build a custom coverage index with package-level grouping, sortable columns, or filtered view. | |
| All of the above | All three: link from pytest test report, branch coverage data, custom-grouped index. | ✓ |

**User's choice:** All of the above
**Notes:** Phase 15 delivers all three additions simultaneously.

---

## Integration with pytest report

### Link location

| Option | Description | Selected |
|--------|-------------|----------|
| Test-level link | Each test row gets a link to the coverage index page. Simpler — doesn't require knowing which source files each test touches. | ✓ |
| File-level inline link | Each test's step table shows source module as a clickable link to its coverage page. Requires parsing step module paths. | |
| Report header/footer link | Single 'Coverage Report' link in report header/footer. Global, not per-test. | |

**User's choice:** Test-level link

### Path strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Relative paths | Use relative paths like coverage/index.html from reports/. Consistent with Phase 13 pattern for screenshots/videos. Works offline. | ✓ |
| Absolute paths | Use absolute filesystem paths. Breaks if reports/ is moved or shared. | |

**User's choice:** Relative paths

---

## Branch coverage data

### Enable branch coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, enable branch coverage | Set branch=true in .coveragerc. Tracks both sides of each conditional. Per-file HTML shows partial branches in yellow. Deferred in Phase 14. | ✓ |
| No, statement coverage only | Keep current line-only measurement. | |

**User's choice:** Yes, enable branch coverage

### Branch columns in index

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, alongside line coverage | Custom index shows: File | Stmts | Miss | Branch | BrPart | Cover%. Matches JaCoCo-style metrics. | ✓ |
| No, just statement coverage columns | Custom index mirrors coverage.py's current columns. | |

**User's choice:** Yes, branch columns alongside line coverage

---

## Custom index vs coverage.py default

### Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped by package | Files organized under their src/ package as collapsible sections. Each section shows aggregate coverage %. Files link to z_*.html pages. JaCoCo-style layout. | ✓ |
| Flat sorted table | Same flat list as coverage.py's index.html but with branch columns and sortable by any column. | |
| Low-coverage first | Flat list auto-sorted by coverage% ascending. | |

**User's choice:** Grouped by package

### Output file location

| Option | Description | Selected |
|--------|-------------|----------|
| reports/coverage/custom_index.html | Sits alongside coverage.py's index.html. Per-file links continue to point to existing z_*.html pages. Zero disruption. | ✓ |
| reports/coverage_drilldown.html | Top-level in reports/ like the pytest HTML report. More visible but outside the coverage/ subdirectory. | |

**User's choice:** reports/coverage/custom_index.html

---

## Add parameter for enable code coverage in pytest

### Coverage flag behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Add --no-cov flag | Coverage runs by default but can be turned off with pytest --no-cov. Useful when running a single quick test without coverage overhead. | ✓ |
| Default off, opt-in with --with-cov | Remove coverage from addopts. Developers opt in when they want coverage. | |
| Keep always-on, no change | Leave addopts as-is. Coverage runs on every pytest invocation. | |

**User's choice:** Add --no-cov flag (opt-out)
**Notes:** pytest-cov's built-in `--no-cov` flag is already supported; no custom flag needed.

### Flag scope

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, skip everything | When coverage is disabled, neither coverage.py HTML nor custom_index.html is generated. Consistent behavior. | ✓ |
| No, generate custom_index from last .coverage | Regenerate custom_index.html from last .coverage data even when --no-cov is passed. More complex. | |

**User's choice:** Yes, skip everything when --no-cov is passed

---

## Generation and Styling

### Generation trigger

| Option | Description | Selected |
|--------|-------------|----------|
| pytest hook — after every run | Wire a pytest_sessionfinish hook that reads .coverage data and writes custom_index.html. Same lifecycle as coverage.py HTML generation. | ✓ |
| Separate CLI command | A standalone Python script run separately after pytest. | |

**User's choice:** pytest hook — after every run

### Visual style

| Option | Description | Selected |
|--------|-------------|----------|
| Reference coverage.py CSS | Link to coverage.py's generated style_cb_*.css. Visual consistency with per-file pages. No extra styling to maintain. | ✓ |
| Plain HTML only | No CSS dependency — pure structural HTML table. | |
| Inline minimal CSS | Small inline <style> block. Self-contained. | |

**User's choice:** Reference coverage.py CSS

---

## Claude's Discretion

- CSS filename discovery strategy for `style_cb_*.css`
- Exact hook/attribute for detecting `--no-cov` state in conftest
- Whether to add constants to `src/core/constants.py` for coverage directory/filename

## Deferred Ideas

- Minimum threshold enforcement (`--cov-fail-under`) — post-baseline
- XML report for CI tools
- Per-test source file mapping (linking each test to its specific per-file coverage page)
- Coverage badge in README
