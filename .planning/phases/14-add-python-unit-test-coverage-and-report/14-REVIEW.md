---
phase: 14-add-python-unit-test-coverage-and-report
reviewed: 2026-05-30T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - .coveragerc
  - .gitignore
  - pytest.ini
  - requirements.txt
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-05-30
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 14 wired pytest-cov into the project by adding the dependency to `requirements.txt`, extending `pytest.ini`'s `addopts`, creating `.coveragerc` for coverage scope, and updating `.gitignore` for the HTML report directory. The configuration is internally consistent — all three config files agree on `src` as the measurement target and `reports/coverage` as the HTML output directory.

One gap was found: the `.coverage` data file that pytest-cov writes to the project root on every run is not excluded in `.gitignore`. There is also a redundancy between `pytest.ini` and `.coveragerc` that is worth resolving for long-term maintainability.

## Warnings

### WR-01: `.coverage` data file not excluded from git

**File:** `.gitignore`
**Issue:** `pytest-cov` writes a `.coverage` binary data file to the project root after every test run (default `data_file` location). This file is not excluded in `.gitignore`. Without the exclusion, developers who run `pytest` will see `.coverage` appear as an untracked file on every run, and it risks being accidentally committed.
**Fix:** Add `.coverage` to `.gitignore`. Optionally also add `.coverage.*` to cover parallel-mode shards:

```gitignore
.coverage
.coverage.*
```

Add these lines alongside the other pytest-related exclusion `.pytest_cache/`.

## Info

### IN-01: `--cov=src` in `pytest.ini` duplicates `source = src` in `.coveragerc`

**File:** `pytest.ini:14`
**Issue:** `addopts` includes `--cov=src`, which sets the coverage source to `src` via the CLI. `.coveragerc` also declares `source = src` under `[run]`. Coverage.py merges these at runtime with CLI flags winning, so there is no functional conflict today. However, having two authoritative definitions of the coverage scope means a future change to one may not be reflected in the other, causing silent drift.
**Fix:** Remove `--cov=src` from `addopts` and rely solely on `.coveragerc` for scope configuration. This keeps the single-source-of-truth in `.coveragerc`:

```ini
# pytest.ini line 14 — remove --cov=src, keep the report flags
addopts = -v --tb=short --cov --cov-report=term-missing --cov-report=html:reports/coverage
```

`--cov` without an argument uses the `source` list from `.coveragerc`, eliminating the duplication.

---

_Reviewed: 2026-05-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
