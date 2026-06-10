# Phase 21: Support locator value from workflow parameters - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Let a locator's `value` reference a workflow parameter so that selectors can be
parameterized at runtime. Example: `{"by": "id", "value": "${company_code}"}`
resolves `company_code` from the workflow `params` block — the same parameter
mechanism Phase 17 added for element *values*, now extended to locators.

Unlike element values (Phase 4/17: anchored full-value-only expansion), locators
need **partial/embedded** expansion because real CSS/XPath selectors usually embed
the parameter inside a larger string (e.g. `//div[@data-company='${company_code}']`,
`#row-${id}`).

**In scope:** Resolving `${param}` tokens embedded anywhere inside `locator.value`,
sourced from the workflow `params` block, on element locators.

**Out of scope:** Changing element-value expansion behavior (stays anchored
full-value-only — no regression); resolving `${env:KEY}` or dynamic generators
(`${sin_number}`, `${first_name}`, etc.) inside locators; whether non-element
locators (pre_wait/post_wait conditions, load_criteria, spinner_locator,
overlay_locator) also expand — left to planner/research to determine the cleanest
seam (see Open Questions).

</domain>

<decisions>
## Implementation Decisions

### Expansion shape
- **D-01:** Locator values support **partial/embedded** expansion — every
  `${param}` found anywhere in the selector string is expanded, not just a
  full-value token. E.g. `//div[@id='${company_code}']` and `#row-${id}` both work.
- **D-02:** This requires a **non-anchored** scan/replace path for locators,
  distinct from the existing anchored `_PLACEHOLDER_PATTERN` (`^\$\{([^}]+)\}$`)
  used for element values.

### Reach (what this changes)
- **D-03:** Partial/embedded expansion applies to **locators only**. Element
  values keep Phase 4's deliberate anchored full-value-only behavior unchanged —
  no regression risk to the 402 existing unit tests. The codebase will have two
  distinct expansion modes (anchored for values, partial for locators), which is
  accepted.

### Resolution sources
- **D-04:** Embedded locator tokens resolve **from the workflow `params` block
  only**. `${env:KEY}` and dynamic generators (`${sin_number}`, `${first_name}`,
  `${random_number}`, etc.) are NOT resolved inside locators — this matches the
  phase's stated intent ("locator value from workflow parameters") and avoids
  nonsensical random-generator-in-selector.

### Unknown-token behavior
- **D-05:** An embedded `${token}` that is **not** a defined workflow param causes
  a **raise / fail-loud** — the step is recorded FAILED with a clear message
  naming the missing param. Consistent with Phase 17's full-value behavior
  (unknown `${x}` → `ValueError`). Catches selector typos immediately rather than
  surfacing as a confusing element-not-found error.

### Claude's Discretion
- Exact regex used for the non-anchored scan, the new function/method name, and
  whether the partial resolver lives in `value_resolver.py` alongside
  `resolve_dynamic_value` or in a dedicated helper.
- Where params are threaded for locator resolution. Today `LocatorResolver.resolve()`
  is a static method with no `params` access and is the single chokepoint
  (`LocatorDefinition` → `(By, value)` tuple) used by element actions, the
  `skip_if_not_visible` visibility probe, and wait/page-readiness locators.
  Planner decides whether to (a) thread `params` into `LocatorResolver`, (b) resolve
  `locator.value` upstream in `ActionFactory` before the resolver, or (c) another seam.
- Exact wording of the error and log messages.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Parameter expansion (prior art — Phase 17)
- `src/actions/value_resolver.py` — `resolve_dynamic_value(value, params)` is the
  Phase 17 expansion engine: env → registry → params tiers, anchored
  `_PLACEHOLDER_PATTERN` (`^\$\{([^}]+)\}$`, full-value-only). The new partial
  locator path must NOT change this anchored behavior (D-03).
- `src/actions/action_factory.py` — constructs `ValueResolver(params=params)`;
  shows how `params` reaches the action layer from `WorkflowEngine`.

### Locator resolution (integration point)
- `src/locators/locator_resolver.py` — `LocatorResolver.resolve(locator, element_name)`
  static method, single chokepoint converting `LocatorDefinition` → `(By, value)`,
  currently returns `locator.value` raw. Used by element actions, the
  `skip_if_not_visible` probe (`action_factory.py:44`), and wait/readiness locators.
- `src/models/workflow_models.py` — `LocatorDefinition` (`by`, `value`) and
  `ElementDefinition`.

### Params plumbing
- `src/data/json_loader.py` — where the `parameters` block is parsed and the
  `params` dict is built (`params[p["name"]] = resolved_value`).
- `src/workflow/workflow_engine.py:61,132` — `self._params` built and passed into
  `ActionFactory(section, self._wm, params=self._params)`.

No external ADRs/specs — this is a self-contained framework feature; requirements
fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `resolve_dynamic_value` / `ValueResolver` (`value_resolver.py`): the params dict
  and tier logic already exist; the new partial resolver can reuse the params dict
  and live alongside it.
- `LocatorResolver.resolve` (`locator_resolver.py`): the single seam where
  `locator.value` becomes a Selenium selector — natural place (or just-before it)
  to apply expansion.

### Established Patterns
- Phase 4 anchored full-value regex is intentional ("no partial substitution —
  prevents partial expansion bugs", per PROJECT.md Key Decisions). The new locator
  path is explicitly a *second* mode (D-03), not a replacement.
- `params: dict | None = None` plumbing pattern (Phase 11/17) — params flow
  WorkflowEngine → ActionFactory → ValueResolver.

### Integration Points
- `LocatorResolver.resolve` is static and params-unaware today — the main wiring
  decision (Claude's discretion D in decisions) is how to give locator resolution
  access to `params`.

</code_context>

<specifics>
## Specific Ideas

- Roadmap example: locator `value: "${company_code}"` resolved from `params`.
- User confirmed embedded usage matters (e.g. `//div[@id='${company_code}']`,
  `#row-${id}`) — partial expansion is the point, not full-value.

</specifics>

<deferred>
## Deferred Ideas

- **Non-element locator expansion** (pre_wait/post_wait conditions, load_criteria,
  spinner_locator, overlay_locator): not discussed/locked. If the implementation
  applies expansion at `LocatorResolver.resolve` (the shared chokepoint), these may
  come along automatically; if applied upstream in `ActionFactory`, they would not.
  Planner/research should surface this and pick the cleanest seam — treat broad
  coverage as acceptable but not a hard requirement for this phase.
- **`${env:KEY}` / dynamic generators inside locators**: explicitly out of scope
  (D-04). Could be a future enhancement if a real need appears.

</deferred>

---

*Phase: 21-support-locator-value-from-workflow-parameters-e-g-locator-v*
*Context gathered: 2026-06-09*
