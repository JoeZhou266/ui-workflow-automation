# Phase 14: Add Python Unit Test Coverage and Report - Pattern Map

**Mapped:** 2026-05-30
**Files analyzed:** 4
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `requirements.txt` | config | — | `requirements.txt` (self — extend) | exact |
| `pytest.ini` | config | — | `pytest.ini` (self — extend) | exact |
| `.coveragerc` | config | — | Phase 13 `.gitignore` / `pytest.ini` addopts pattern | role-match |
| `.gitignore` | config | — | `.gitignore` (self — extend) | exact |

---

## Pattern Assignments

### `requirements.txt` (config — extend in-place)

**Analog:** `requirements.txt` itself

**Current file** (`requirements.txt` lines 1–8):
```
selenium>=4.15.0
pytest>=7.4.0
pydantic>=2.0.0
PyYAML>=6.0.0
python-dotenv>=1.0.0
allure-pytest>=2.13.0
webdriver-manager>=4.0.0
pytest-html>=4.0.0
```

**Pattern from Phase 13 addition of `pytest-html`:** append a single line at the end of the file following the `plugin>=X.Y.Z` convention. No section headers, no comments — flat list only.

**Line to append:**
```
pytest-cov>=4.0.0
```

After the edit the file reads:
```
selenium>=4.15.0
pytest>=7.4.0
pydantic>=2.0.0
PyYAML>=6.0.0
python-dotenv>=1.0.0
allure-pytest>=2.13.0
webdriver-manager>=4.0.0
pytest-html>=4.0.0
pytest-cov>=4.0.0
```

---

### `pytest.ini` (config — extend in-place)

**Analog:** `pytest.ini` itself

**Current `addopts` line** (`pytest.ini` line 14):
```ini
addopts = -v --tb=short
```

**Extension rule from CONTEXT.md (D-08):** append three coverage flags to `addopts` without changing any other key. All flags go on the same `addopts` line — `pytest.ini` does not support multi-line `addopts` continuation in this project's existing style.

**Updated line:**
```ini
addopts = -v --tb=short --cov=src --cov-report=term-missing --cov-report=html:reports/coverage
```

**Rationale for flag choices:**
- `--cov=src` — scope matches D-02 (all of `src/`)
- `--cov-report=term-missing` — D-04 terminal summary with uncovered line numbers visible (D-09 specifics)
- `--cov-report=html:reports/coverage` — D-04/D-06 HTML output to `reports/coverage/`
- No `--cov-fail-under` — D-09 defers threshold enforcement

**Full updated file** (only `addopts` line changes):
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)s] %(name)s: %(message)s
log_cli_date_format = %H:%M:%S
markers =
    smoke: end-to-end tests requiring a real browser
    unit: unit tests with no browser dependency
    slow: tests that take more than a few seconds
addopts = -v --tb=short --cov=src --cov-report=term-missing --cov-report=html:reports/coverage
```

---

### `.coveragerc` (config — new file)

**Analog:** No direct codebase analog exists. The closest structural parallel is `pytest.ini` (INI-style config file at repo root with section headers and key = value pairs) and the `.gitignore` reports-block pattern (per-artifact subdirectory exclusion). Coverage.py `.coveragerc` follows standard INI format identical to `pytest.ini`.

**File to create at repo root (`.coveragerc`):**
```ini
[run]
source = src
omit =
    src/**/__init__.py

[html]
directory = reports/coverage
```

**Design rationale:**
- `[run] source = src` — D-02: measure all of `src/`; coverage.py reads this when `--cov=src` is also set (no conflict, they reinforce each other)
- `[run] omit = src/**/__init__.py` — D-03: exclude re-export-only init files from measurement
- `[html] directory = reports/coverage` — D-06/D-07: canonical reports subdirectory; mirrors `reports/screenshots/` and `reports/videos/` convention
- Using `.coveragerc` rather than `[coverage:run]` in `setup.cfg` — project has no `setup.cfg`; and separating coverage config from `pytest.ini` keeps `pytest.ini` `addopts` line shorter (CONTEXT.md Claude's Discretion)
- No `[report]` section — D-09: no threshold (`fail_under`)
- No `branch = true` — deferred per CONTEXT.md Deferred section

---

### `.gitignore` (config — extend in-place)

**Analog:** `.gitignore` itself

**Existing reports block** (`.gitignore` lines 15–21):
```
# Reports / screenshots / videos (keep dir, ignore contents)
reports/screenshots/
reports/videos/
reports/*.html
reports/*.xml
reports/assets/
allure-results/
allure-report/
```

**Phase 12 precedent** — `reports/videos/` was added on the line immediately after `reports/screenshots/`, with the comment updated from `# Reports / screenshots` to `# Reports / screenshots / videos`. Phase 14 follows the same pattern: add `reports/coverage/` after `reports/assets/` and update the comment.

**Updated reports block:**
```
# Reports / screenshots / videos / coverage (keep dirs, ignore contents)
reports/screenshots/
reports/videos/
reports/*.html
reports/*.xml
reports/assets/
reports/coverage/
allure-results/
allure-report/
```

**Rule:** one new line `reports/coverage/` appended after `reports/assets/` (line 20), comment on line 15 extended to mention coverage.

---

## Shared Patterns

### INI-file extension style
**Source:** `pytest.ini` lines 1–14, `.gitignore` lines 15–21
**Apply to:** `pytest.ini` (addopts extension), `.coveragerc` (new file)

Both config files in this project use flat key = value under section headers, no quoted values, no trailing whitespace. Multi-value lists in `.coveragerc` (e.g., `omit`) use one-value-per-line with leading whitespace (standard coverage.py convention):
```ini
omit =
    src/**/__init__.py
```

### Plugin dependency pinning style
**Source:** `requirements.txt` lines 7–8
```
webdriver-manager>=4.0.0
pytest-html>=4.0.0
```
**Apply to:** `requirements.txt` — new `pytest-cov` line uses same `>=X.Y.Z` lower-bound pinning, no upper bound, no `==` exact pin.

### `reports/` subdirectory gitignore pattern
**Source:** `.gitignore` lines 15–20
```
reports/screenshots/
reports/videos/
reports/*.html
reports/*.xml
reports/assets/
```
**Apply to:** `.gitignore` — `reports/coverage/` follows the trailing-slash directory pattern used by every other `reports/` entry. The comment on line 15 is updated to enumerate the new artifact type.

---

## No Analog Found

All four files have direct codebase analogs (three are self-extensions, one mirrors INI format from `pytest.ini`). No files require falling back to RESEARCH.md patterns exclusively.

---

## Metadata

**Analog search scope:** `requirements.txt`, `pytest.ini`, `.gitignore`, `.planning/phases/12-support-video-capture/12-PATTERNS.md`, `.planning/phases/13-generate-html-test-report/13-PATTERNS.md`
**Files scanned:** 7
**Pattern extraction date:** 2026-05-30
