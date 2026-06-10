# Phase 21: Support locator value from workflow parameters - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** 21-support-locator-value-from-workflow-parameters-e-g-locator-v
**Areas discussed:** Expansion shape

---

## Gray-area selection

| Area | Description | Selected |
|------|-------------|----------|
| Expansion shape | Full-value-only vs partial/embedded `${param}` in locator strings | ✓ |
| Locator scope | Element locators only vs also wait/load_criteria/spinner/overlay | |
| Resolution sources | Full resolver tiers vs params-only | |
| Unknown-param behavior | Raise vs leave literal | |

**Note:** User selected only "Expansion shape". The partial/embedded choice forced
follow-up decisions that overlapped the other (unselected) areas, so reach, sources,
and unknown-token behavior were resolved within the Expansion-shape thread.

---

## Expansion shape

### Q1 — What expansion shape should locator values support?

| Option | Description | Selected |
|--------|-------------|----------|
| Partial/embedded | Expand every `${param}` anywhere in the locator string (e.g. `//div[@id='${company_code}']`, `#row-${id}`). Requires a non-anchored regex path. | ✓ |
| Full-value only | Locator value must be exactly `"${param}"` (matches roadmap example + Phase 4 anchored regex). | |

**User's choice:** Partial/embedded

### Q2 — Should partial/embedded expansion apply only to locators, or also element values?

| Option | Description | Selected |
|--------|-------------|----------|
| Locators only | New partial path used only for `locator.value`; element values keep Phase 4 anchored behavior. Two expansion modes. | ✓ |
| Unify everywhere | Make partial expansion the behavior for both locators and element values; changes the deliberate Phase 4 decision. | |

**User's choice:** Locators only
**Notes:** Avoids regression risk to the 402 existing unit tests.

### Q3 — Which token sources should each embedded `${...}` in a locator resolve against?

| Option | Description | Selected |
|--------|-------------|----------|
| All sources | `${env:KEY}` → dynamic generators → params, same tiers as element values. | |
| Params only | Resolve only from the workflow `params` block; `${sin_number}`/`${env:KEY}` stay unresolved. | ✓ |

**User's choice:** Params only
**Notes:** Matches the phase's stated intent and avoids nonsensical random-generator-in-selector.

### Q4 — When an embedded locator token isn't a defined workflow param, what should happen?

| Option | Description | Selected |
|--------|-------------|----------|
| Raise (fail loud) | Step recorded FAILED with a clear message naming the missing param. Consistent with Phase 17. | ✓ |
| Leave literal | Leave `${token}` verbatim and let Selenium fail on element-not-found. | |

**User's choice:** Raise (fail loud)

---

## Claude's Discretion

- Exact non-anchored regex, helper name, and whether the partial resolver lives in
  `value_resolver.py` or a dedicated helper.
- How `params` are threaded to locator resolution (`LocatorResolver` is currently a
  static, params-unaware chokepoint) — thread into the resolver vs resolve upstream
  in `ActionFactory`.
- Error and log message wording.

## Deferred Ideas

- Non-element locator expansion (pre_wait/post_wait, load_criteria, spinner_locator,
  overlay_locator) — not locked; planner to pick the cleanest seam.
- `${env:KEY}` / dynamic generators inside locators — explicitly out of scope; possible
  future enhancement.
