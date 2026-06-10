---
phase: 21
slug: support-locator-value-from-workflow-parameters-e-g-locator-v
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-09
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml / pytest.ini (existing) |
| **Quick run command** | `pytest tests/unit/ -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~15 seconds (unit) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/ -q`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-----------|--------|
| 21-01-XX | 01 | 1 | locator partial expansion | — | N/A | unit | `pytest tests/unit/ -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Concrete task IDs filled in by planner; key behaviors to validate: (1) embedded `${param}` expands anywhere in selector, (2) multiple tokens in one selector, (3) unknown token raises ValueError naming the param, (4) anchored element-value path unchanged (regression).*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_locator_param_expansion.py` — new test file for partial locator expansion
- [ ] Existing `tests/unit/` fixtures cover params plumbing

*Existing pytest infrastructure covers the framework; only new test cases needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification (input selector + params → expected resolved selector is a pure-function assertion).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
