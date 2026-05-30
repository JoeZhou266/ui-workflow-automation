# Phase 11: Support Workflow Parameters + Conditional $ref — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 11-support-workflow-parameters-conditional-ref
**Areas discussed:** Parameter declaration scope, Condition expressiveness, Condition-false behavior, Parameter value types and sources

---

## Parameter Declaration Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Workflow root only | parameters is only a field on WorkflowDefinition. All sub-levels inherit workflow parameters read-only. Simpler model, no merge logic needed. | ✓ |
| Multi-level: each level can add/override | Tabs, pages, sections can each declare their own parameters that extend or shadow parent params. More powerful but adds merge/precedence rules. | |
| Workflow + Tab level only | Workflow and each TabDefinition can declare parameters. Pages and sections inherit from their parent tab. Middle ground. | |

**User's choice:** Workflow root only (Recommended)
**Notes:** Simple model — no merge/precedence needed.

---

## Condition Expressiveness

| Option | Description | Selected |
|--------|-------------|----------|
| Equality only: == and != | Support ${param} == 'value' and ${param} != 'value'. Covers 95% of real use cases with minimal parser complexity. | ✓ |
| Equality + set membership: ==, !=, in | Add in ['A','B','C'] for multi-value checks. | |
| Full expression: ==, !=, in, and, or, not | Boolean composition for complex conditions. Much more parser complexity. | |

**User's choice:** Equality only: == and != (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Raise a clear error at load time | Fail fast — undefined param in a condition is a workflow authoring mistake and should surface immediately. | ✓ |
| Treat undefined param as empty string, condition = false | Silent skip. | |
| Treat undefined param as empty string, condition = true | Permissive — missing param lets the $ref through. | |

**User's choice:** Raise a clear error at load time (Recommended)

---

## Condition-False Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Silently omit from parent list | The $ref node is filtered out of its parent list (tabs, pages, sections). No warning, no empty placeholder. | ✓ |
| Omit + log at DEBUG level | Same as silent omit but emits a debug log line. | |
| Omit + log at INFO level | More visible logging. | |

**User's choice:** Silently omit from parent list (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| All levels: tabs, pages, sections, elements | Conditional $ref works anywhere. | |
| Top 3 only: tabs, pages, sections (not elements) | Elements are already individually skippable via skip_if_not_visible (Phase 7). | ✓ |

**User's choice:** Top 3 only: tabs, pages, sections (not elements)

---

## Parameter Value Types and Sources

| Option | Description | Selected |
|--------|-------------|----------|
| Strings only | All parameter values are strings. Simple, no type-coercion edge cases. | ✓ |
| String and boolean | bool values like true/false allow flag-style parameters. | |
| Any JSON scalar | Full flexibility but requires type-aware comparison logic. | |

**User's choice:** Strings only (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — resolve env placeholders in parameter values at load time | Allows parameters: [{name: account_type, value: '${env:ACCOUNT_TYPE}'}]. Powerful composition with Phase 10. | ✓ |
| No — static values only in Phase 11 | Parameter values are literal strings only. | |

**User's choice:** Yes — resolve env placeholders in parameter values at load time (Recommended)

---

## Claude's Discretion

- Where to implement `evaluate_condition()` — new module vs. inline in json_loader.py
- Whether `resolve_refs()` uses a `params: dict` parameter or a class-based approach

## Deferred Ideas

- Multi-level parameters (tab/page/section-level overrides)
- Operators beyond == and != (contains, in, and/or)
- Element-level conditional $ref
