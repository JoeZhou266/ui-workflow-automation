---
phase: 04-support-dynamic-placeholder-expansion
plan: "01"
subsystem: actions
tags: [placeholder-expansion, value-resolver, tdd, sin-generator, canadian-sin, luhn]
dependency_graph:
  requires: []
  provides:
    - PLACEHOLDER_REGISTRY in src/actions/value_resolver.py
    - resolve_dynamic_value() function
    - generate_sin_number() with Luhn mod-10 validation
    - generate_first_name() / generate_last_name() generators
    - ValueResolver._resolve_string() wired to resolve_dynamic_value()
  affects:
    - src/actions/action_factory.py (caller — no change needed, already wired)
tech_stack:
  added: [re (stdlib), random (stdlib)]
  patterns: [registry + function dispatch, anchored regex fullmatch, Luhn mod-10 algorithm, unittest.mock.patch.dict for registry isolation]
key_files:
  created:
    - tests/unit/test_value_resolver.py
  modified:
    - src/actions/value_resolver.py
decisions:
  - "Full-value-only token matching: anchored regex `^\\$\\{([^}]+)\\}$` — partial-token values like 'prefix_${sin_number}' return unchanged"
  - "ValueError raised for unknown placeholder keys — fail-fast over silent passthrough"
  - "No external dependencies — stdlib random + static name lists sufficient; Faker not installed"
  - "PLACEHOLDER_REGISTRY stores callables not pre-computed strings — each call produces a fresh value"
metrics:
  duration: "1m 45s"
  completed_date: "2026-05-20"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  tests_added: 24
  tests_total: 167
---

# Phase 04 Plan 01: Dynamic Placeholder Expansion Summary

**One-liner:** Registry-based `${placeholder}` token resolution in `ValueResolver._resolve_string()` with Canadian SIN Luhn-validated generator, name generators, and anchored-regex full-value-only matching.

## What Was Built

Expanded `src/actions/value_resolver.py` from a 31-line pass-through stub into a full placeholder resolution engine. When a workflow JSON element `value` field contains a token like `${sin_number}`, `ValueResolver.resolve()` now dispatches through `resolve_dynamic_value()` to a registered generator function at action-dispatch time, returning a generated value instead of the literal string.

The existing call site in `action_factory.py:42` (`_resolver.resolve(element.value)`) required no changes — it was already wired to `ValueResolver.resolve()`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write test file RED | 4afed4b | tests/unit/test_value_resolver.py (created) |
| 2 | Implement production code GREEN | 92399f9 | src/actions/value_resolver.py (expanded) |

## TDD Gate Compliance

- RED gate: commit `4afed4b` — `test(04-01): add failing tests for placeholder resolution (RED)` — all 24 tests failed with `ImportError: cannot import name 'PLACEHOLDER_REGISTRY'`
- GREEN gate: commit `92399f9` — `feat(04-01): implement placeholder expansion in value_resolver.py (GREEN)` — all 24 tests pass, 167 total unit tests green

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/unit/test_value_resolver.py::TestGenerators -v` | 7 passed |
| `pytest tests/unit/test_value_resolver.py::TestPlaceholderRegistry -v` | 11 passed |
| `pytest tests/unit/test_value_resolver.py::TestValueResolverIntegration -v` | 6 passed |
| `pytest tests/unit/test_value_resolver.py -v` | 24 passed |
| `pytest tests/unit/ -v` | 167 passed (no regressions) |
| `pytest tests/unit/test_action_dispatch.py::TestValueResolver -v` | 4 passed |

## Success Criteria Met

- SC-1: `PLACEHOLDER_REGISTRY` exported at module level with `sin_number`, `first_name`, `last_name` keys — confirmed
- SC-2: `resolve_dynamic_value()` resolves full-value tokens, passes through partial/plain strings, raises `ValueError` for unknown placeholders — confirmed
- SC-3: `ValueResolver.resolve("${sin_number}")` returns a 9-digit string — confirmed
- SC-4: `generate_sin_number()` passes Luhn mod-10 check (20 iterations), first digit 1–8 (50 iterations) — confirmed
- SC-5: `generate_first_name()` and `generate_last_name()` return non-empty strings — confirmed
- SC-6: Full test file (24 tests) exits 0 — confirmed

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all placeholder expansion is fully implemented and wired.

## Threat Flags

None — the new surface (PLACEHOLDER_REGISTRY callable dispatch) uses only statically defined module-level functions; no user-supplied callables are accepted; no exec/eval. Consistent with threat model T-04-05 disposition: accept.

## Self-Check: PASSED

- `tests/unit/test_value_resolver.py` exists: FOUND
- `src/actions/value_resolver.py` has PLACEHOLDER_REGISTRY: FOUND
- Commit `4afed4b` exists: FOUND (test RED)
- Commit `92399f9` exists: FOUND (feat GREEN)
- 167 unit tests pass: CONFIRMED
