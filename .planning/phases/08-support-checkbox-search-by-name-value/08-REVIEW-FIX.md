---
phase: 08-support-checkbox-search-by-name-value
fixed_at: 2026-05-26T22:58:30Z
review_path: .planning/phases/08-support-checkbox-search-by-name-value/08-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 8: Code Review Fix Report

**Fixed at:** 2026-05-26T22:58:30Z
**Source review:** .planning/phases/08-support-checkbox-search-by-name-value/08-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: CSS selector injection via unsanitised `locator.value` and `value` arguments

**Files modified:** `src/ui/base_page.py`
**Commit:** 74a8f28
**Applied fix:** Added module-level `_css_escape_attr(value: str) -> str` helper that replaces `"` with `\"`. Applied it to `locator.value` and `value` interpolation in all three affected methods: `check()`, `uncheck()`, and `select_radio()`. Each now uses a multi-line f-string with `_css_escape_attr()` wrapping both dynamic values.

---

### WR-02: `test_check_with_name_locator_and_value_builds_css_selector` only tests the already-checked (no-click) path

**Files modified:** `tests/unit/test_action_dispatch.py`
**Commit:** 1226ea1
**Applied fix:** Extended both `test_check_with_name_locator_and_value_builds_css_selector` and `test_uncheck_with_name_locator_and_value_builds_css_selector` to include a second case within each test. For `check()`: added a `not_yet_checked_el` with `is_selected.return_value = False` and asserted `click.assert_called_once()`. For `uncheck()`: added a `currently_checked_el` with `is_selected.return_value = True` and asserted `click.assert_called_once()`. All 34 unit tests pass.

---

_Fixed: 2026-05-26T22:58:30Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
