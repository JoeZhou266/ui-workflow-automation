---
phase: 10-support-env-placeholder
plan: "01"
subsystem: testing
tags: [python, selenium, pytest, value-resolver, placeholder, env-config]

# Dependency graph
requires:
  - phase: 09-support-last-day-of-month-placeholder
    provides: "generate_last_day_of_next_month generator, PLACEHOLDER_REGISTRY pattern, resolve_dynamic_value() function"
provides:
  - "_ENV_CONFIG module-level dict in value_resolver.py populated from YAML env file"
  - "configure_env_resolver() function to wire YAML data into the resolver module"
  - "env: branch in resolve_dynamic_value() for ${env:KEY} placeholder support"
  - "AppConfig.__init__ wires configure_env_resolver so env dict is populated before action dispatch"
  - "8 new TestEnvPlaceholder tests covering SC-1..SC-4"
affects: [workflow-runner, action-dispatch, env-config]

# Tech tracking
tech-stack:
  added: []
  patterns: ["env: namespace prefix in placeholder tokens for env YAML key lookup", "module-level singleton dict pattern for shared resolver state"]

key-files:
  created: []
  modified:
    - "src/actions/value_resolver.py"
    - "src/core/config.py"
    - "tests/unit/test_value_resolver.py"

key-decisions:
  - "D-01: env: prefix in placeholder token name routes to _ENV_CONFIG dict, not PLACEHOLDER_REGISTRY — clean namespace separation with no regex change needed"
  - "D-02: configure_env_resolver() uses global _ENV_CONFIG = data assignment (replaces entire dict) — simple, test-isolable singleton"
  - "D-03: ValueError message discloses available key names (not values) — acceptable tradeoff for debuggability per threat model T-10-04"

patterns-established:
  - "env: namespace in ${env:KEY} tokens routes to _ENV_CONFIG dict before PLACEHOLDER_REGISTRY lookup"
  - "configure_env_resolver() called once in AppConfig.__init__ after _load_yaml() — ensures env dict is populated before any workflow action dispatch"

requirements-completed: [SC-1, SC-2, SC-3, SC-4]

# Metrics
duration: 3min
completed: 2026-05-30
---

# Phase 10 Plan 01: Support env-placeholder Summary

**${env:KEY} placeholder resolution wired from YAML env config through _ENV_CONFIG module singleton into resolve_dynamic_value() with ValueError on missing keys**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-30T02:49:26Z
- **Completed:** 2026-05-30T02:52:55Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 3

## Accomplishments
- Added `_ENV_CONFIG: dict = {}` and `configure_env_resolver()` to `value_resolver.py` — populates module singleton from AppConfig YAML data
- Added `env:` branch in `resolve_dynamic_value()` — checks `_ENV_CONFIG` before `PLACEHOLDER_REGISTRY`, raises `ValueError` with available keys on miss
- Wired `configure_env_resolver(self._data)` into `AppConfig.__init__` immediately after `_load_yaml()` call
- Added 8 new `TestEnvPlaceholder` tests covering SC-1 through SC-4 (all pass)
- All 212 unit tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for TestEnvPlaceholder** - `04a5bc2` (test)
2. **Task 2 (GREEN): Implement _ENV_CONFIG, configure_env_resolver, env: branch, AppConfig wiring** - `aa982bc` (feat)

_Note: TDD plan — test commit (RED gate) precedes feat commit (GREEN gate)._

## Files Created/Modified
- `src/actions/value_resolver.py` - Added `_ENV_CONFIG` dict, `configure_env_resolver()` function, `env:` branch in `resolve_dynamic_value()`
- `src/core/config.py` - Added `from src.actions.value_resolver import configure_env_resolver` import and `configure_env_resolver(self._data)` call in `__init__`
- `tests/unit/test_value_resolver.py` - Added `configure_env_resolver` to import block, appended `TestEnvPlaceholder` class with 8 tests, fixed pre-existing SIN test expectations

## Decisions Made
- env: namespace prefix routes to `_ENV_CONFIG` dict before `PLACEHOLDER_REGISTRY` — no regex change needed as `_PLACEHOLDER_PATTERN` already captures `env:KEY` as group(1)
- `configure_env_resolver()` uses `global _ENV_CONFIG = data` (replaces entire dict) — simple, enables test isolation by resetting per test
- ValueError message includes `Available keys: {sorted(_ENV_CONFIG)}` (key names only, not values) — acceptable per threat model T-10-04

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing SIN test expectations to match chunked generate_sin_number() behavior**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** `TestGenerators` (test_sin_length, test_sin_first_digit, test_sin_luhn_valid), `TestPlaceholderRegistry::test_resolve_sin_number`, `TestValueResolverIntegration::test_resolver_expands_sin`, and `TestEnvPlaceholder::test_env_and_registry_placeholders_coexist` all expected `len(generate_sin_number()) == 9` but `generate_sin_number()` returns 3-digit chunks in a 3-call cycle. This pre-existing bug was introduced in a prior phase when the SIN generator was refactored to return chunks for multi-field form input.
- **Fix:** Updated failing tests to call `generate_sin_number()` 3 times and concatenate chunks to assemble the full 9-digit SIN before asserting length/validity. Added `_full_sin()` helper method in `TestGenerators`. No changes to `value_resolver.py` implementation — the chunked behavior is correct by design.
- **Files modified:** `tests/unit/test_value_resolver.py`
- **Verification:** `pytest tests/unit/ -v` exits 0 with 212 tests passing
- **Committed in:** `aa982bc` (Task 2 feat commit)

---

**Total deviations:** 1 auto-fixed (1 pre-existing bug in test expectations)
**Impact on plan:** Fix was necessary for the plan's success criteria (`pytest tests/unit/ -v` exits 0). No scope creep — only corrected test assertions to match documented chunked SIN generator behavior.

## Issues Encountered
- Pre-existing SIN test failures (introduced in an earlier phase when `generate_sin_number()` was changed from returning a 9-digit SIN to returning 3-digit chunks for multi-field form input). Tests expected the old behavior. Fixed as Rule 1 auto-fix.

## User Setup Required
None - no external service configuration required.

## TDD Gate Compliance

| Gate | Commit | Type |
|------|--------|------|
| RED | `04a5bc2` | `test(10-01)` |
| GREEN | `aa982bc` | `feat(10-01)` |

Both gates present and in correct order. No REFACTOR gate needed — no cleanup required.

## Next Phase Readiness
- `${env:KEY}` placeholder resolution complete and tested
- Any workflow JSON can use `${env:base_url}`, `${env:account_number}`, etc. to reference env YAML values
- `configure_env_resolver()` is called automatically when `AppConfig` is instantiated — no manual wiring needed per workflow

---
*Phase: 10-support-env-placeholder*
*Completed: 2026-05-30*
