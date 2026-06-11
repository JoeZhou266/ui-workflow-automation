# Phase 22: Support updating a group of similar web elements together - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Expand a **single element definition** in the workflow JSON into a **group of
indexed element interactions** — all sharing the same element type, action, and
value — where the element names/locators differ only by a numeric index.

Examples from the roadmap:
- `amount_0`, `amount_1`, `amount_2` … (index appended)
- `bank_0_account`, `bank_1_account` … (index embedded mid-string)

The author writes one element using an `${index}` token plus a range field; the
framework loops over the range, substituting the index into the name and locator
on each iteration and running the same action/value. This layers a loop variable
on top of the existing `${param}` expansion seams from Phase 17 (element values)
and Phase 21 (partial locator expansion).

**In scope:** A new per-element range field that drives iteration; `${index}`
token substitution (embedded anywhere) in element `name` and `locator.value`;
one StepResult recorded per index; same value applied to every index.

**Out of scope:** Per-index distinct values (deferred — see Deferred Ideas);
dynamic runtime discovery of how many indexed elements exist (range is
author-declared, static); non-numeric/named iteration; nested/multi-dimensional
indices (e.g. row×column).

</domain>

<decisions>
## Implementation Decisions

### Authoring shape
- **D-01:** A group is declared as a **single element definition** carrying an
  `${index}` token plus a new **`index_range`** field. The framework loops over
  the range, substituting the index per iteration. Reuses the Phase 17/21
  `${param}` expansion machinery (index behaves like a loop-scoped param).
- **D-02:** Range syntax is **`index_range: [start, end]`, inclusive on both
  ends.** `[0, 3]` produces indices 0, 1, 2, 3 (four elements). Chosen because it
  reads naturally as "from 0 to 3" for JSON authors (lower off-by-one risk than
  Python-style exclusive end).

### Index token
- **D-03:** The token is **`${index}`**, substituted **embedded anywhere** inside
  both the element **`name`** and the **`locator.value`**. This handles
  mid-string cases like `bank_${index}_account` and `//input[@id='amount_${index}']`,
  not just suffix `amount_${index}`. Mirrors Phase 21's partial (non-anchored)
  locator expansion.
- **D-04:** Substituting `${index}` into the **name** is required so each result
  row shows the concrete per-index name (`amount_0`, `amount_1`, …), not a generic
  group label.

### Per-index value
- **D-05:** For this phase, **all indices receive the same `value`** — matches the
  roadmap phrasing "same element type, action, and value." Simplest correct
  behavior for the stated use case.
- **D-06:** **Design the field so a future phase can supply per-index values
  without breaking existing JSON.** Don't paint the schema into a corner: a later
  enhancement should be able to accept a list of per-index values as an additive,
  backward-compatible change. (Per-index values are NOT implemented now — see
  Deferred Ideas.)

### Result & failure semantics
- **D-07:** Record **one StepResult per index** (e.g. `amount_0` PASS,
  `amount_1` FAIL, `amount_2` PASS). Each iteration is its own step for full
  visibility in logs/reports.
- **D-08:** **Continue the group on a failed index** — a failing index does NOT
  stop the remaining indices in the group. (Consistent with the existing
  per-element continue-on-failure model in `WorkflowEngine._run_element`.)
- **D-09:** **Missing index honors the element's `skip_if_not_visible`.** If a
  declared index isn't present on the page and the element opts in via
  `skip_if_not_visible`, that index records **SKIPPED** (not FAILED); otherwise a
  missing index is a normal action failure (FAILED, group continues). Reuses the
  existing per-element skip behavior — author opts into tolerance for sparse
  groups rather than the framework guessing.

### Claude's Discretion
- Exact field/model name on `ElementDefinition` and Pydantic validation (e.g.
  `index_range: Optional[List[int]]` with a length-2, start≤end validator).
- The seam where index expansion happens: whether the engine expands a single
  `ElementDefinition` into N concrete elements before `_run_element`, or threads
  the index into the existing `${param}`/locator resolution path. (Planner/research
  should pick the cleanest seam — note `${index}` must reach BOTH name and locator
  substitution, and the per-index value/skip behavior must be preserved.)
- The token/regex used for `${index}` substitution and how it composes with the
  Phase 17 anchored value path and Phase 21 partial locator path (index is a
  distinct loop-scoped source from workflow `params`).
- Whether `${index}` is reserved (cannot collide with a workflow `param` named
  `index`) and how that's enforced/messaged.
- Exact wording of error/log messages.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Direct prior art — index is a loop-scoped `${param}` (READ FIRST)
- `.planning/phases/21-support-locator-value-from-workflow-parameters-e-g-locator-v/21-CONTEXT.md`
  — Phase 21 added **partial/embedded** `${param}` expansion in `locator.value`
  (non-anchored). `${index}` substitution in locators should follow the same
  non-anchored pattern.
- `.planning/phases/17-support-parameter-value-expansion/` (CONTEXT/PLAN) — Phase 17
  added `${param_name}` expansion in element **values** (anchored, full-value-only).
  Establishes the `params` → ValueResolver plumbing the index can reuse.

### Expansion engine (integration points)
- `src/actions/value_resolver.py` — `resolve_dynamic_value(value, params)`:
  env → registry → params tiers; anchored `_PLACEHOLDER_PATTERN`
  (`^\$\{([^}]+)\}$`). Element-value expansion (D-05 same value) flows through here.
- `src/locators/locator_resolver.py` — `LocatorResolver.resolve(locator, element_name)`,
  the single `LocatorDefinition` → `(By, value)` chokepoint; Phase 21 added partial
  `${param}` expansion here. `${index}` in locators substitutes on this path.
- `src/actions/action_factory.py` — `ActionFactory(section, wm, params=params)`;
  constructs `ValueResolver(params=params)` and runs the `skip_if_not_visible`
  visibility probe (relevant to D-09).

### Models & engine (where the new field + loop live)
- `src/models/workflow_models.py` — `ElementDefinition` (add the `index_range`
  field here; note existing `skip_if_not_visible` handling and model validators)
  and `LocatorDefinition`.
- `src/workflow/workflow_engine.py` — `_run_section` / `_run_element` loop and the
  per-element continue-on-failure + SkipElementSignal handling (D-07/D-08/D-09).
  This is where one element must expand into N per-index steps.
- `src/data/json_loader.py` — where the workflow JSON / `params` block is parsed.

No external ADRs/specs — this is a self-contained framework feature; requirements
fully captured in the decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`${param}` expansion stack** (`value_resolver.py` + Phase 21 locator path in
  `locator_resolver.py`): the index is conceptually a loop-scoped parameter — the
  substitution machinery for both values and locators already exists and should be
  reused, not reinvented.
- **`skip_if_not_visible` per-element behavior** (`SkipElementSignal` handled in
  `WorkflowEngine._run_element`): D-09's missing-index tolerance is exactly this
  existing path applied per index.
- **Per-element continue-on-failure** (`_run_element` records FAIL and returns,
  loop proceeds): D-08's "continue group on fail" falls out of the existing model
  if each index is run as its own element-step.

### Established Patterns
- `params: dict | None = None` plumbing (Phase 11/17/21): `WorkflowEngine` →
  `ActionFactory` → `ValueResolver`. The index needs to reach BOTH the value path
  and the locator path on each iteration.
- Two expansion modes coexist: anchored full-value for element values (Phase 4/17),
  partial/embedded for locators (Phase 21). `${index}` must work in both, embedded
  (D-03/D-04 require substitution inside `name` and `locator.value`).

### Integration Points
- `WorkflowEngine._run_section` iterates `section.elements` and calls
  `_run_element` once per element. The cleanest seam likely expands one
  indexed `ElementDefinition` into N concrete per-index runs around/inside this
  loop so the existing result-recording, skip, and failure handling apply unchanged.
- `LocatorResolver.resolve` is static and `params`-aware only via Phase 21's wiring;
  index threading must follow whatever seam Phase 21 chose.

</code_context>

<specifics>
## Specific Ideas

- Roadmap examples to support verbatim: `amount_0`/`amount_1` (suffix index) and
  `bank_0_account`/`bank_1_account` (embedded mid-string index) — both must work
  via `${index}` (D-03).
- Authoring example the planner can target:
  ```json
  {
    "name": "amount_${index}",
    "type": "number",
    "action": "input",
    "locator": { "by": "id", "value": "amount_${index}" },
    "index_range": [0, 3],
    "value": "100"
  }
  ```
  → runs `amount_0..amount_3`, each set to `100`, each its own result row.

</specifics>

<deferred>
## Deferred Ideas

- **Per-index distinct values** — supplying a list of values mapped per index
  (e.g. `value: ["100","200","300"]`). Explicitly out of scope now (D-05), but the
  schema must stay open to it as a backward-compatible addition (D-06). Candidate
  for a future phase.
- **Dynamic count discovery** — having the framework count matching indexed
  elements on the page at runtime instead of an author-declared `index_range`.
  Considered and rejected for this phase (range is static). Possible future
  enhancement if a real need appears.
- **Non-contiguous / explicit index lists** (e.g. `indices: [0,1,2,5]`) and
  **multi-dimensional indices** (row×column) — out of scope; `index_range` covers
  the contiguous case the roadmap describes.

</deferred>

---

*Phase: 22-support-updating-a-group-of-similar-web-elements-together-sa*
*Context gathered: 2026-06-11*
