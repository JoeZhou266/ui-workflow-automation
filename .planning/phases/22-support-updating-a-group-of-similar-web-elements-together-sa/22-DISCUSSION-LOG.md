# Phase 22: Support updating a group of similar web elements together - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 22-support-updating-a-group-of-similar-web-elements-together-sa
**Areas discussed:** Authoring shape, Index token, Per-index value, Result & failure, Range syntax, Missing index

---

## Authoring shape

| Option | Description | Selected |
|--------|-------------|----------|
| Index token + range field | One element with `${index}` token + a range field; framework loops, reusing Phase 17/21 `${param}` machinery | ✓ |
| Explicit index list | Author lists exact indices (`indices: [0,1,2,5]`); handles sparse groups | |
| Dynamic count from page | Framework discovers count at runtime; no hardcoded range | |

**User's choice:** Index token + range field
**Notes:** Layers a loop variable on existing expansion seams; range is author-declared (static).

---

## Index token

| Option | Description | Selected |
|--------|-------------|----------|
| Embedded anywhere, in name + locator | `${index}` substitutes anywhere in both name and locator value; handles `bank_${index}_account` | ✓ |
| Locator value only | Index expands only in locator; name stays a static group label | |

**User's choice:** Embedded anywhere, in name + locator
**Notes:** Mirrors Phase 21 partial locator expansion; per-index name needed so result rows show concrete names.

---

## Per-index value

| Option | Description | Selected |
|--------|-------------|----------|
| Same value for all (roadmap default) | All indices get the one `value` | |
| Same now, allow per-index later | Lock same-value this phase; design field so a future phase can add per-index values without breaking JSON | ✓ |

**User's choice:** Same now, allow per-index later
**Notes:** Per-index values deferred but schema must stay backward-compatible-open.

---

## Result & failure

| Option | Description | Selected |
|--------|-------------|----------|
| One result per index, continue on fail | Each index its own StepResult; failed index doesn't stop the rest | ✓ |
| One result per index, abort group on fail | Per-index results, but first failure stops remaining indices | |
| Single rolled-up result | Whole group is one StepResult | |

**User's choice:** One result per index, continue on fail
**Notes:** Falls out of the existing per-element continue-on-failure model in `WorkflowEngine._run_element`.

---

## Range syntax

| Option | Description | Selected |
|--------|-------------|----------|
| index_range: [start, end] inclusive | `[0,3]` → 0,1,2,3; token `${index}` | ✓ |
| count + optional start | `index_count: 4` (+ `index_start`) → 0..3 | |
| index_range: [start, end) exclusive | `[0,4]` → 0,1,2,3 (Python range semantics) | |

**User's choice:** index_range: [start, end] inclusive
**Notes:** Reads naturally "from 0 to 3"; lower off-by-one risk for JSON authors.

---

## Missing index

| Option | Description | Selected |
|--------|-------------|----------|
| Fail that index (default) | Absent declared index → FAILED, group continues | |
| Honor element's skip_if_not_visible | Missing index → SKIPPED if `skip_if_not_visible` set, else FAILED | ✓ |

**User's choice:** Honor element's skip_if_not_visible
**Notes:** Reuses existing per-element skip behavior; author opts into tolerance for sparse groups.

---

## Claude's Discretion

- Exact field/model name + Pydantic validation for `index_range`.
- The seam where index expansion happens (expand to N elements before `_run_element` vs thread index into resolution).
- Token/regex for `${index}` and composition with Phase 17 anchored value path + Phase 21 partial locator path.
- Whether `${index}` is reserved vs collides with a workflow `param` named `index`, and enforcement.
- Exact error/log message wording.

## Deferred Ideas

- Per-index distinct values (e.g. `value: ["100","200","300"]`) — schema stays open to it (D-06).
- Dynamic count discovery at runtime — rejected for this phase.
- Non-contiguous explicit index lists and multi-dimensional (row×column) indices — out of scope.
