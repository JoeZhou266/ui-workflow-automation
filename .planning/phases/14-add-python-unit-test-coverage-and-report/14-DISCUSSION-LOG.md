# Phase 14: Add Python unit test coverage and report - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 14-add-python-unit-test-coverage-and-report
**Areas discussed:** Coverage scope, Report format & location

---

## Coverage scope

| Option | Description | Selected |
|--------|-------------|----------|
| All of src/ | Measure all 9 subpackages. Browser-only modules show as uncovered — honest picture. | ✓ |
| src/ minus browser modules | Exclude src/driver/ and src/ui/ from coverage. | |
| Core logic only | Measure src/core/, src/models/, src/data/, src/actions/, src/workflow/ only. | |

**User's choice:** All of src/ (Recommended)
**Notes:** Accepted the honest picture — browser-dependent lines will appear uncovered in unit test runs, which is expected and acceptable.

---

| Option | Description | Selected |
|--------|-------------|----------|
| No exclusions | All lines in src/ counted. | |
| Exclude __init__.py files | Init files are re-exports; excluding them raises % without hiding real gaps. | ✓ |
| You decide | Apply standard pragma exclusions only. | |

**User's choice:** Exclude `__init__.py` files
**Notes:** Cleaner reported percentage without masking genuine coverage gaps.

---

## Report format & location

| Option | Description | Selected |
|--------|-------------|----------|
| Terminal summary + HTML | Terminal per-file % table + HTML to reports/coverage/. | ✓ |
| Terminal summary only | No files written, fast. | |
| Terminal + HTML + XML | Adds coverage.xml for CI tools. | |

**User's choice:** Terminal summary + HTML (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| reports/coverage/ | Consistent with existing reports/ convention. | ✓ |
| htmlcov/ at project root | pytest-cov default, breaks convention. | |

**User's choice:** reports/coverage/ (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Always on — add to addopts | Every pytest run measures coverage. | ✓ |
| Opt-in via --cov flag | Only runs when explicitly passed. | |

**User's choice:** Always on — add to addopts (Recommended)

---

## Claude's Discretion

- Coverage config file format (`.coveragerc` vs inline in `pytest.ini`)
- `.gitignore` update for `reports/coverage/`
- Whether a `COVERAGE_DIR` constant is needed in `src/core/constants.py`

## Deferred Ideas

- Minimum threshold enforcement (`--cov-fail-under`) — deferred until baseline % known
- XML report for CI tools (Codecov, SonarQube)
- Coverage badge in README
- Branch coverage (`branch = true`)
- Per-run timestamped HTML coverage snapshots
